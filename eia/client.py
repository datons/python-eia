import requests
import logging
import pandas as pd
import re
from urllib.parse import urlparse, parse_qs
from typing import (
    List,
    Dict,
    Optional,
    Union,
    Any,
    Literal,
    TypeVar,
    Generic,
    Type,
    Protocol,
    runtime_checkable,
)
import os
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

T = TypeVar("T")


class EIAError(Exception):
    """Custom exception for EIA API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        api_error_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.api_error_code = api_error_code

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status_code:
            parts.append(f"HTTP Status Code: {self.status_code}")
        if self.api_error_code:
            parts.append(f"API Error Code: {self.api_error_code}")
        return " | ".join(parts)


@dataclass
class FacetValue:
    """Represents a single value for a facet with its metadata."""

    id: str
    name: str
    description: Optional[str] = None


@dataclass
class FrequencyInfo:
    """Metadata for a specific data frequency."""

    id: str
    description: str
    query: str
    format: str


@dataclass
class DataColumnInfo:
    """Metadata for a specific data column."""

    id: str
    aggregation_method: Optional[str] = None
    alias: Optional[str] = None
    units: Optional[str] = None


@dataclass
class FacetInfo:
    """Metadata for a specific facet."""

    id: str
    description: Optional[str] = None
    # Store the route slug for potential API calls
    _route_slug: Optional[str] = field(default=None, repr=False)
    _client: Optional["EIAClient"] = field(default=None, repr=False)

    def get_values(self) -> List[FacetValue]:
        """Fetches and returns all possible values for this facet."""
        if not self._client or not self._route_slug:
            raise ValueError("Client and route slug must be set to fetch facet values.")

        response = self._client.get_facet_values(self._route_slug, self.id)
        return [
            FacetValue(
                id=value["id"],
                name=value.get("name", value["id"]),
                description=value.get("description"),
            )
            for value in response.get("facets", [])
        ]


@runtime_checkable
class FacetContainerProtocol(Protocol):
    """Protocol defining the interface for facet containers."""

    _facets: Dict[str, FacetInfo]

    def __getattr__(self, name: str) -> FacetInfo: ...
    def __getitem__(self, key: str) -> FacetInfo: ...
    def keys(self) -> List[str]: ...
    def items(self) -> List[tuple[str, FacetInfo]]: ...
    def values(self) -> List[FacetInfo]: ...


class BaseFacetContainer:
    """Base container class for facets to allow attribute-based access."""

    def __init__(self, facets: Dict[str, FacetInfo]) -> None:
        self._facets = facets

    def __getattr__(self, name: str) -> FacetInfo:
        """
        Access facets as attributes using underscores instead of hyphens.

        Args:
            name: The facet name to access

        Returns:
            The FacetInfo object for the requested facet

        Raises:
            AttributeError: If no facet with the given name exists
        """
        # Try with underscores and hyphens
        if name in self._facets:
            return self._facets[name]

        # Try with hyphenated version
        hyphenated = name.replace("_", "-")
        if hyphenated in self._facets:
            return self._facets[hyphenated]

        raise AttributeError(f"No facet named '{name}' exists")

    def __getitem__(self, key: str) -> FacetInfo:
        """Dictionary-style access for backward compatibility."""
        try:
            return self.__getattr__(key)
        except AttributeError as e:
            raise KeyError(str(e))

    def __dir__(self) -> List[str]:
        """Customize dir() output to show available facets for autocomplete."""
        # Get the facet names in both formats
        facet_names = []
        for name in self._facets:
            facet_names.append(name)
            if "-" in name:
                facet_names.append(name.replace("-", "_"))
        return sorted(set(facet_names + super().__dir__()))

    def keys(self) -> List[str]:
        """Return facet keys."""
        return list(self._facets.keys())

    def items(self) -> List[tuple[str, FacetInfo]]:
        """Return facet items."""
        return list(self._facets.items())

    def values(self) -> List[FacetInfo]:
        """Return facet values."""
        return list(self._facets.values())

    def __repr__(self) -> str:
        """Provide a helpful representation of available facets."""
        facets_str = ", ".join(self._facets.keys())
        return f"FacetContainer(facets=[{facets_str}])"


def create_facet_container(
    facets: Dict[str, FacetInfo],
) -> Type[FacetContainerProtocol]:
    """
    Creates a typed FacetContainer class with attributes for the given facets.

    Args:
        facets: Dictionary of facet information

    Returns:
        A new FacetContainer subclass with typed attributes for the given facets
    """

    def make_getter(facet_name: str):
        """Create a getter function for the property that properly captures the facet name."""
        return lambda self: self._facets[facet_name]

    class_attrs = {
        # Convert class docstring to show available facets
        "__doc__": "Container for facets with attribute access.\n\nAvailable facets:\n"
        + "\n".join(
            f"    {k}: {v.description or 'No description'}" for k, v in facets.items()
        ),
        # Store the facets dict
        "_facets": facets,
    }

    # Add each facet as a typed property
    for name, info in facets.items():
        # Create both hyphenated and underscore versions of the property
        underscore_name = name.replace("-", "_")
        class_attrs[underscore_name] = property(
            fget=make_getter(name), doc=f"{info.description or 'No description'}"
        )

        # If the name contains hyphens, also add the hyphenated version as an alias
        if "-" in name:
            class_attrs[name] = property(
                fget=make_getter(name), doc=f"{info.description or 'No description'}"
            )

    # Create the class with proper name and bases
    return type("TypedFacetContainer", (BaseFacetContainer,), class_attrs)


class FacetContainer(BaseFacetContainer):
    """Container for facets with dynamic attribute access."""

    def __new__(cls, facets: Dict[str, FacetInfo]) -> "FacetContainer":
        """
        Create a new FacetContainer instance with typed attributes.

        Args:
            facets: Dictionary mapping facet IDs to their FacetInfo objects
        """
        # Create a new typed subclass for these specific facets
        container_class = create_facet_container(facets)
        # Create an instance of the typed container class
        instance = object.__new__(container_class)
        instance._facets = facets
        return instance

    def __init__(self, facets: Dict[str, FacetInfo]) -> None:
        """
        Initialize with a dictionary of facets.

        Args:
            facets: Dictionary mapping facet IDs to their FacetInfo objects
        """
        # __init__ is called after __new__, but we already initialized _facets in __new__
        pass


class Data:
    """Represents a data endpoint in the EIA API with its metadata and query capabilities."""

    def __init__(self, client: "EIAClient", route: str, metadata: Dict[str, Any]):
        self._client = client
        self._route = route
        self._metadata = metadata
        self.id = metadata.get("id", route.split("/")[-1])
        self.name = metadata.get("name", "")
        self.description = metadata.get("description", "")

        # Initialize attributes to store fetched data and metadata
        self.dataframe: Optional[pd.DataFrame] = None
        self.last_response_metadata: Optional[Dict[str, Any]] = None

        self.frequencies: List[FrequencyInfo] = [
            FrequencyInfo(
                id=freq["id"],
                description=freq.get("description", ""),
                query=freq.get("query", ""),
                format=freq.get("format", ""),
            )
            for freq in metadata.get("frequency", [])
            if isinstance(freq, dict) and "id" in freq
        ]

        facet_dict = {
            facet_data["id"]: FacetInfo(
                id=facet_data["id"],
                description=facet_data.get("description"),
                _route_slug=route,  # Pass route slug
                _client=client,  # Pass client instance
            )
            for facet_data in metadata.get("facets", [])
            if isinstance(facet_data, dict) and "id" in facet_data
        }
        # Use FacetContainer for attribute-based access
        self.facets = FacetContainer(facet_dict)

        self.data_columns: Dict[str, DataColumnInfo] = {}
        for col_id, col_data in metadata.get("data", {}).items():
            if isinstance(col_data, dict):
                self.data_columns[col_id] = DataColumnInfo(
                    id=col_id,
                    aggregation_method=col_data.get("aggregation-method"),
                    alias=col_data.get("alias"),
                    units=col_data.get("units"),
                )

        self.start_period = metadata.get("startPeriod")
        self.end_period = metadata.get("endPeriod")
        self.default_date_format = metadata.get("defaultDateFormat")
        self.default_frequency = metadata.get("defaultFrequency")

    def __dir__(self) -> List[str]:
        """Customize dir() output for better IDE support."""
        return sorted(list(self.__dict__.keys()) + ["get"])

    def get(
        self,
        data_columns: Optional[List[str]] = None,
        facets: Optional[Dict[str, Union[str, List[str]]]] = None,
        frequency: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        length: Optional[int] = None,
        offset: Optional[int] = None,
        output_format: Optional[Literal["json", "xml"]] = "json",
        paginate: bool = True,
    ) -> pd.DataFrame:
        """
        Retrieves data from this endpoint, stores it and metadata internally,
        and returns the data as a pandas DataFrame. Handles pagination automatically by default.

        Args:
            data_columns: List of data column IDs to retrieve. If None, all available columns are fetched.
            facets: Dictionary of facet filters, e.g., {'stateid': 'CA', 'sectorid': ['RES', 'COM']}
            frequency: Data frequency ID (e.g., 'daily', 'monthly')
            start: Start date/period
            end: End date/period
            sort: List of sort specifications
            length: Maximum number of rows to return *if paginate=False*. Ignored if paginate=True.
            offset: Starting row offset for the first request.
            output_format: Response format ('json' or 'xml'). Must be 'json' for DataFrame conversion.
            paginate: Whether to automatically paginate through results (default: True).

        Returns:
            A pandas DataFrame containing the requested data
        """
        # Use column IDs if data_columns is None
        column_ids_to_fetch = (
            data_columns if data_columns is not None else list(self.data_columns.keys())
        )

        # Ensure output is json if we want a DataFrame
        if output_format != "json":
            logging.warning(
                "output_format must be 'json' to return a DataFrame. Forcing to JSON."
            )
            output_format = "json"

        all_data = []
        current_offset = offset if offset is not None else 0
        first_request = True
        API_PAGE_LIMIT = 5000  # Standard EIA API limit for JSON

        while True:
            request_length = None if paginate else length

            logging.info(
                f"Fetching data for route: {self._route} - Offset: {current_offset}, Length: {request_length or 'All (Pagination)'}"
            )

            response_data = self._client.get_data(
                route=self._route,
                data_columns=column_ids_to_fetch,
                facets=facets,
                frequency=frequency,
                start=start,
                end=end,
                sort=sort,
                length=request_length,  # Use calculated length
                offset=current_offset,  # Use current offset
                output_format=output_format,
            )

            if first_request:
                # Store metadata from the first response
                self.last_response_metadata = {
                    k: v for k, v in response_data.items() if k != "data"
                }
                first_request = False

            # Extract data chunk
            data_chunk = response_data.get("data", [])

            if not data_chunk:  # No more data
                logging.info("Received empty data chunk, stopping pagination.")
                break

            all_data.extend(data_chunk)
            logging.info(f"Received {len(data_chunk)} rows.")

            # Stop if not paginating or if last page received
            if not paginate or len(data_chunk) < API_PAGE_LIMIT:
                if not paginate:
                    logging.info("Pagination disabled, stopping after one request.")
                else:
                    logging.info("Received less than page limit, assuming end of data.")
                break

            # Prepare for next page
            current_offset += API_PAGE_LIMIT

        # Convert combined data to DataFrame
        df = pd.DataFrame(all_data)

        # --- Automatic Preprocessing ---
        # Convert 'period' column to datetime if it exists
        if "period" in df.columns:
            try:
                if frequency is not None and "local" not in frequency.lower():
                    df["period"] = pd.to_datetime(
                        df["period"], errors="coerce", utc=True
                    )
                    logging.info(
                        "Automatically converted 'period' column to datetime with UTC."
                    )
                else:
                    df["period"] = pd.to_datetime(df["period"], errors="coerce")
                    logging.info("Automatically converted 'period' column to datetime.")
            except Exception as e:
                logging.warning(
                    f"Could not automatically convert 'period' column to datetime: {e}"
                )

        # Convert 'value' column to numeric if it exists
        if "value" in df.columns:
            try:
                # Attempt conversion, coercing errors to NaN
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                logging.info("Automatically converted 'value' column to numeric.")
            except Exception as e:
                logging.warning(
                    f"Could not automatically convert 'value' column to numeric: {e}"
                )
        # --- End Automatic Preprocessing ---

        # Store DataFrame
        self.dataframe = df

        return df


class Route:
    """
    Represents a route in the EIA API that can contain either nested routes or data.

    Attributes:
        routes (Dict[str, 'Route']): Available child routes if this is a route container
        data (Data): Data object if this endpoint contains data
    """

    def __init__(
        self,
        client: "EIAClient",
        slug: str,
    ):
        """
        Initialize a route.

        Args:
            client: The EIA client instance
            slug: The route path (e.g., 'electricity/retail-sales')
        """
        self._client = client
        self._slug = slug.strip("/")
        self._metadata: Optional[Dict[str, Any]] = None
        self._routes: Dict[str, "Route"] = {}
        self._data: Optional[Data] = None

    def _ensure_metadata(self) -> None:
        """Lazily loads metadata when needed."""
        if self._metadata is None:
            self._metadata = self._client.get_metadata(self._slug)
            response_data = self._metadata

            # Check if routes exist in the response dictionary
            if "routes" in response_data:
                for route in response_data["routes"]:
                    route_id = route["id"]
                    attr_name = route_id.replace("-", "_")
                    # Create placeholder Route objects without fetching their metadata
                    if attr_name not in self._routes:
                        self._routes[attr_name] = Route(
                            self._client,
                            f"{self._slug}/{route_id}",
                        )

            # If response doesn't contain routes, it means this endpoint has data
            if "routes" not in response_data:
                self._data = Data(self._client, self._slug, response_data)

    def __getattr__(self, name: str) -> Union["Route", Any]:
        """
        Access child routes or data attributes.
        Always returns a Route object for navigation.

        Args:
            name: The attribute name to access

        Returns:
            A Route object for the requested path

        Raises:
            AttributeError: If the route doesn't exist
        """
        # Ensure metadata is loaded first
        self._ensure_metadata()

        # Try with underscores and hyphens
        if name in self._routes:
            return self._routes[name]

        # Try with hyphenated version
        hyphenated = name.replace("_", "-")
        if hyphenated in self._routes:
            return self._routes[hyphenated]

        # If nothing is found, raise AttributeError
        raise AttributeError(
            f"'{type(self).__name__}' object for route '{self._slug}' has no attribute '{name}'"
        )

    def __getitem__(self, key: str) -> "Route":
        """
        Access child routes using dictionary-style access.
        Allows both underscore and hyphen formats.

        Args:
            key: The route key to access

        Returns:
            A Route object for the requested path

        Raises:
            KeyError: If the route doesn't exist
        """
        try:
            return self.__getattr__(key)
        except AttributeError as e:
            raise KeyError(str(e))

    def keys(self) -> List[str]:
        """Returns available route keys."""
        self._ensure_metadata()
        return list(self._routes.keys())

    def __iter__(self):
        """Allows iteration over available routes."""
        return iter(self.keys())

    def __dir__(self) -> List[str]:
        """
        Customize dir() output to show available routes.
        This helps with IDE autocompletion.
        """
        self._ensure_metadata()
        attributes = set(super().__dir__())
        attributes.update(self._routes.keys())
        if self._data is not None:
            attributes.add("data")
        return sorted(attributes)

    @property
    def routes(self) -> Dict[str, "Route"]:
        """Returns available child routes."""
        self._ensure_metadata()
        return self._routes

    @property
    def data(self) -> Data:
        """Returns the Data object if this endpoint contains data."""
        self._ensure_metadata()
        if self._data is not None:
            return self._data
        raise AttributeError(
            f"Route '{self._slug}' does not contain data. It has child routes: {list(self._routes.keys())}"
        )


class EIAClient:
    """A client for interacting with the U.S. Energy Information Administration (EIA) API v2."""

    BASE_URL = "https://api.eia.gov/v2/"
    # Regex to parse structured URL parameters like sort[0][column]
    _param_regex = re.compile(
        r"^([a-zA-Z_\-]+)(?:\[(\d+)\])?(?:\[([a-zA-Z_\-]+)\])?(?:\[\])?$"
    )

    def __init__(
        self, api_key: Optional[str] = None, session: Optional[requests.Session] = None
    ):
        """
        Initializes the EIAClient.

        Args:
            api_key: Your EIA API key. If None, it will try to read from the EIA_API_KEY environment variable.
            session: An optional requests.Session object for persistent connections.
        """
        resolved_api_key = api_key or os.environ.get("EIA_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "API key is required. Provide it directly or set the EIA_API_KEY environment variable."
            )
        self.api_key = resolved_api_key
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "Python EIAClient"})
        logging.info("EIAClient initialized.")

    def route(self, slug: str) -> Route:
        """
        Access an API route by its slug.

        Args:
            slug: The route path (e.g., 'electricity/retail-sales')

        Returns:
            A Route object representing the requested endpoint
        """
        return Route(self, slug)

    def _build_url(self, route: str) -> str:
        """Constructs the full API URL for a given route."""
        route = route.strip("/")
        return f"{self.BASE_URL}{route}"

    def _prepare_params(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepares parameters, adding the API key."""
        final_params = params.copy() if params else {}
        final_params["api_key"] = self.api_key
        return final_params

    def _format_list_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Formats list-based parameters for URL encoding."""
        formatted_params = {}
        list_params_to_process = {}

        for key, value in params.items():
            if key == "data" and isinstance(value, list):
                list_params_to_process[key] = value
            elif key == "facets" and isinstance(value, dict):
                list_params_to_process[key] = value
            elif key == "sort" and isinstance(value, list):
                list_params_to_process[key] = value
            else:
                formatted_params[key] = value

        if "data" in list_params_to_process:
            for i, col in enumerate(list_params_to_process["data"]):
                formatted_params[f"data[]"] = col

        if "facets" in list_params_to_process:
            facet_dict = list_params_to_process["facets"]
            for facet_id, values in facet_dict.items():
                if isinstance(values, list):
                    for val in values:
                        formatted_params[f"facets[{facet_id}][]"] = val
                else:
                    formatted_params[f"facets[{facet_id}][]"] = values

        if "sort" in list_params_to_process:
            sort_list = list_params_to_process["sort"]
            for i, sort_item in enumerate(sort_list):
                if isinstance(sort_item, dict) and "column" in sort_item:
                    formatted_params[f"sort[{i}][column]"] = sort_item["column"]
                    if "direction" in sort_item:
                        formatted_params[f"sort[{i}][direction]"] = sort_item[
                            "direction"
                        ]

        return formatted_params

    def _send_request(
        self,
        method: str,
        route: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sends an HTTP request to the EIA API."""
        full_url = self._build_url(route)
        base_params = self._prepare_params({})
        request_params = params.copy() if params else {}
        request_params.update(base_params)
        formatted_url_params = self._format_list_params(request_params)

        logging.debug(
            f"Sending {method} request to {full_url} with params: {formatted_url_params}"
        )

        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=formatted_url_params,
                json=data,
            )
            response.raise_for_status()
            json_response = response.json()

            if "error" in json_response:
                error_msg = json_response["error"]
                error_code = json_response.get("code")
                logging.error(f"API Error ({error_code}): {error_msg}")
                raise EIAError(
                    error_msg,
                    status_code=response.status_code,
                    api_error_code=error_code,
                )

            if "warning" in json_response:
                warning_msg = json_response.get("description", json_response["warning"])
                logging.warning(f"API Warning: {warning_msg}")

            return json_response

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise EIAError(
                f"HTTP Error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Exception: {e}")
            raise EIAError(f"Request Failed: {e}") from e
        except ValueError as e:
            logging.error(f"Failed to decode JSON response: {e}")
            raise EIAError("Invalid JSON response received from API.") from e

    def get_metadata(self, route: str) -> Dict[str, Any]:
        """Retrieves metadata for a given API route."""
        if route.endswith("/data"):
            route = route[: -len("/data")]
        route = route.strip("/")
        logging.info(f"Fetching metadata for route: {route}")
        response_data = self._send_request("GET", route)
        return response_data.get("response", {})

    def get_facet_values(self, route: str, facet_id: str) -> Dict[str, Any]:
        """Retrieves available values for a specific facet."""
        if route.endswith("/data"):
            route = route[: -len("/data")]
        route = route.strip("/")
        facet_route = f"{route}/facet/{facet_id}"
        logging.info(f"Fetching facet values for facet '{facet_id}' in route: {route}")
        response_data = self._send_request("GET", facet_route)
        return response_data.get("response", {})

    def get_data(
        self,
        route: str,
        data_columns: List[str],
        facets: Optional[Dict[str, Union[str, List[str]]]] = None,
        frequency: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        length: Optional[int] = None,
        offset: Optional[int] = None,
        output_format: Optional[Literal["json", "xml"]] = "json",
    ) -> Dict[str, Any]:
        """Retrieves data points from the EIA API."""
        route = route.strip("/")
        if not route.endswith("/data"):
            data_route = f"{route}/data"
        else:
            data_route = route

        logging.info(f"Fetching data for route: {data_route}")

        params: Dict[str, Any] = {"data": data_columns}

        # Convert FacetContainer to dict if needed
        if facets and hasattr(facets, "_facets"):
            facets = facets._facets

        if facets:
            params["facets"] = facets
        if frequency:
            params["frequency"] = frequency
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if sort:
            params["sort"] = sort
        if length is not None:
            params["length"] = length
        if offset is not None:
            params["offset"] = offset
        if output_format and output_format != "json":
            params["out"] = output_format

        response_data = self._send_request("GET", data_route, params=params)

        if output_format == "xml" and isinstance(response_data, str):
            logging.warning(
                "Received XML response as string. Consider adding XML parsing."
            )
            return {"raw_xml": response_data}

        return response_data.get("response", {})

    def get_data_endpoint(self, route_string: str) -> Data:
        """
        Directly retrieves the Data object for a known, complete data route string.

        This allows bypassing the chained route navigation if the exact data route is known.

        Args:
            route_string: The full route path to the data endpoint
                          (e.g., 'electricity/rto/fuel-type-data').

        Returns:
            The Data object for the specified route.

        Raises:
            EIAError: If the route does not exist or does not contain data.
        """
        route_string = route_string.strip("/")
        logging.info(f"Directly accessing data endpoint metadata for: {route_string}")

        # Fetch metadata for the route
        metadata = self.get_metadata(route_string)

        # Check if the route actually contains data (basic check)
        if "data" not in metadata or "facets" not in metadata:
            # Attempt to find the actual data sub-route if one exists
            possible_data_route = f"{route_string}/data"
            try:
                logging.debug(
                    f"Route '{route_string}' might not be a data endpoint, trying '{possible_data_route}'"
                )
                metadata = self.get_metadata(
                    possible_data_route
                )  # Check if /data exists
                route_string = possible_data_route  # Use the /data route if it exists
                if "data" not in metadata or "facets" not in metadata:
                    raise EIAError(
                        f"Route '{route_string}' does not appear to be a valid data endpoint."
                    )
            except EIAError:
                # If /data doesn't exist or is not a data endpoint either, raise error
                raise EIAError(
                    f"Route '{route_string}' does not appear to be a valid data endpoint and '{possible_data_route}' was not found."
                )

        # Instantiate and return the Data object
        return Data(self, route_string, metadata)

    def get_data_from_url(self, url: str) -> Dict[str, Any]:
        """
        Executes an EIA API v2 data request directly from a provided URL.

        Parses the URL to extract the route and parameters, then sends the request.
        This method respects the offset and length parameters in the URL and does
        *not* perform automatic pagination.

        Args:
            url: The full EIA API v2 data URL (must start with EIAClient.BASE_URL).

        Returns:
            The raw dictionary response from the API for the given URL.

        Raises:
            ValueError: If the URL is invalid or does not match the EIA API base URL.
            EIAError: For API-related errors during the request.
        """
        if not url.startswith(self.BASE_URL):
            raise ValueError(
                f"URL must start with the EIA API base URL: {self.BASE_URL}"
            )

        parsed_url = urlparse(url)
        route_path = parsed_url.path.replace(
            self.BASE_URL.replace("https://api.eia.gov", ""), "", 1
        ).strip("/")
        raw_params = parse_qs(parsed_url.query)

        # Remove api_key from params if present, as it's handled by the client
        raw_params.pop("api_key", None)

        logging.info(
            f"Executing request from URL. Route: {route_path}, Raw Params: {raw_params}"
        )

        # Send the request using the parsed parameters
        # Note: We bypass the high-level get_data and use _send_request directly
        # because the parameter structure from parse_qs needs specific handling
        # and we want to return the raw dict, not force a DataFrame.
        # The _format_list_params method is designed for the structure used by Data.get,
        # not the direct URL query string structure.

        # Convert parsed params (values are lists) back to simple strings where appropriate
        # EIA API typically doesn't expect list format for simple params like frequency, offset, length
        processed_params = {}
        for key, value_list in raw_params.items():
            if (
                isinstance(value_list, list)
                and len(value_list) == 1
                and not key.endswith("[]")
            ):
                # If it's a list of one item and key doesn't suggest a list, take the single item
                processed_params[key] = value_list[0]
            else:
                # Otherwise, keep the list (for facets, data, sort etc.)
                processed_params[key] = value_list

        # We pass the processed_params directly to _send_request which expects a flat dict
        # It will add the api_key itself.
        # The requests library handles the URL encoding of these params including the [] notation.
        return self._send_request("GET", route_path, params=processed_params)

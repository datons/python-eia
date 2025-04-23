import requests
import logging
from typing import List, Dict, Optional, Union, Any, Literal
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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


class EIAClient:
    """
    A client for interacting with the U.S. Energy Information Administration (EIA) API v2.

    Attributes:
        api_key (str): The API key for accessing the EIA API.
        base_url (str): The base URL for the EIA API v2.
        session (requests.Session): A session object for making HTTP requests.
    """

    BASE_URL = "https://api.eia.gov/v2/"

    def __init__(
        self, api_key: Optional[str] = None, session: Optional[requests.Session] = None
    ):
        """
        Initializes the EIAClient.

        Args:
            api_key: Your EIA API key. If None, it will try to read from the
                     EIA_API_KEY environment variable.
            session: An optional requests.Session object for persistent connections.
                     If None, a new session is created.

        Raises:
            ValueError: If the API key is not provided and cannot be found in the
                        EIA_API_KEY environment variable.
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

    def _build_url(self, route: str) -> str:
        """Constructs the full API URL for a given route."""
        # Ensure route doesn't start or end with /
        route = route.strip("/")
        return f"{self.BASE_URL}{route}"

    def _prepare_params(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepares parameters, adding the API key."""
        final_params = params.copy() if params else {}
        final_params["api_key"] = self.api_key
        return final_params

    def _format_list_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats list-based parameters (like data, facets, sort) into the
        structure expected by the EIA API in URL parameters.
        """
        formatted_params = {}
        list_params_to_process = {}  # Store lists temporarily

        for key, value in params.items():
            if key == "data" and isinstance(value, list):
                list_params_to_process[key] = value
            elif key == "facets" and isinstance(value, dict):
                list_params_to_process[key] = value
            elif key == "sort" and isinstance(value, list):
                list_params_to_process[key] = value
            else:
                # Keep non-list params as they are
                formatted_params[key] = value

        # Process data[]
        if "data" in list_params_to_process:
            for i, col in enumerate(list_params_to_process["data"]):
                formatted_params[f"data[{i}]"] = col

        # Process facets[facet_id][]=value
        if "facets" in list_params_to_process:
            facet_dict = list_params_to_process["facets"]
            for facet_id, values in facet_dict.items():
                if isinstance(values, list):
                    for i, val in enumerate(values):
                        # Although docs show facets[id][]=val, requests handles multiple
                        # params with same key correctly, so just use key facets[id]
                        # Note: Let requests handle the [] formatting implicitly
                        # by passing a list for the key 'facets[facet_id]'
                        # However, the API expects facets[id][]=value, so we build it manually
                        # We will stick to the explicit format from docs for safety:
                        formatted_params[f"facets[{facet_id}][]"] = val
                else:  # Handle single value case
                    formatted_params[f"facets[{facet_id}][]"] = values

        # Process sort[index][column/direction]=value
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
        data: Optional[Dict[str, Any]] = None,  # For potential future POST requests
    ) -> Dict[str, Any]:
        """
        Sends an HTTP request to the EIA API.

        Args:
            method: HTTP method (e.g., 'GET').
            route: The API route (e.g., 'electricity/retail-sales').
            params: URL parameters for the request.
            data: Request body data (for POST, PUT, etc.).

        Returns:
            The JSON response from the API.

        Raises:
            EIAError: If the API returns an error or the HTTP request fails.
        """
        full_url = self._build_url(route)
        base_params = self._prepare_params({})  # Just get api_key initially
        request_params = params.copy() if params else {}
        request_params.update(base_params)

        # Format list-based parameters correctly for URL encoding
        formatted_url_params = self._format_list_params(request_params)

        logging.debug(
            f"Sending {method} request to {full_url} with params: {formatted_url_params}"
        )

        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=formatted_url_params,  # Use the formatted params here
                json=data,  # Use json for request body if needed
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            json_response = response.json()

            # Check for API-level errors indicated in the response body
            if "error" in json_response:
                error_msg = json_response["error"]
                error_code = json_response.get("code")
                logging.error(f"API Error ({error_code}): {error_msg}")
                raise EIAError(
                    error_msg,
                    status_code=response.status_code,
                    api_error_code=error_code,
                )

            # Check for warnings (optional: could just log them)
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
        except ValueError as e:  # Catches JSON decoding errors
            logging.error(f"Failed to decode JSON response: {e}")
            raise EIAError("Invalid JSON response received from API.") from e

    def get_metadata(self, route: str) -> Dict[str, Any]:
        """
        Retrieves metadata for a given API route.

        This includes descriptions, available frequencies, facets, child routes, etc.
        It automatically removes '/data' if present in the route.

        Args:
            route: The API route (e.g., 'electricity/retail-sales' or 'electricity').

        Returns:
            A dictionary containing the metadata.
        """
        # Ensure we are requesting metadata, not data points
        if route.endswith("/data"):
            route = route[: -len("/data")]
        route = route.strip("/")  # Clean route
        logging.info(f"Fetching metadata for route: {route}")
        response_data = self._send_request("GET", route)
        return response_data.get("response", {})  # Return the nested 'response' dict

    def get_facet_values(self, route: str, facet_id: str) -> Dict[str, Any]:
        """
        Retrieves available values for a specific facet within a given route.

        Args:
            route: The base API route (e.g., 'electricity/retail-sales').
            facet_id: The ID of the facet to explore (e.g., 'sectorid').

        Returns:
            A dictionary containing the facet values and descriptions.
        """
        # Ensure route doesn't include /data or end with /
        if route.endswith("/data"):
            route = route[: -len("/data")]
        route = route.strip("/")

        facet_route = f"{route}/facet/{facet_id}"
        logging.info(f"Fetching facet values for facet '{facet_id}' in route: {route}")
        response_data = self._send_request("GET", facet_route)
        return response_data.get("response", {})  # Return the nested 'response' dict

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
        output_format: Optional[Literal["json", "xml"]] = "json",  # Added type hint
    ) -> Dict[str, Any]:
        """
        Retrieves data points from the EIA API for a specific route.

        Args:
            route: The API route ending with '/data' is optional, it will be added.
                   (e.g., 'electricity/retail-sales').
            data_columns: A list of data column names to retrieve (e.g., ['price', 'revenue']).
                          Found in the 'data' section of the metadata.
            facets: A dictionary specifying filters. Keys are facet IDs (e.g., 'stateid'),
                    values are either a single value or a list of values (e.g., {'stateid': 'CO', 'sectorid': ['RES', 'COM']}).
            frequency: The desired data periodicity (e.g., 'monthly', 'annual').
                       Found in the 'frequency' section of the metadata.
            start: The start date/period for the data (e.g., '2020-01' or '2020'). Format depends on frequency.
            end: The end date/period for the data (e.g., '2021-12' or '2021'). Format depends on frequency.
            sort: A list of dictionaries for sorting results. Each dict should have
                  'column' (e.g., 'period') and optionally 'direction' ('asc' or 'desc').
                  Example: [{'column': 'period', 'direction': 'desc'}, {'column': 'price'}]
            length: The maximum number of rows to return (for pagination). Max 5000 for JSON, 300 for XML.
            offset: The row number to start returning data from (for pagination).
            output_format: The desired output format ('json' or 'xml'). Defaults to 'json'.

        Returns:
            A dictionary containing the requested data and metadata about the request.
            If output_format='xml', the raw XML string might be returned or handled differently
            depending on parsing needs (currently returns JSON structure even if XML requested,
            needs adjustment if raw XML is desired).
        """
        # Ensure route ends with /data
        route = route.strip("/")
        if not route.endswith("/data"):
            data_route = f"{route}/data"
        else:
            data_route = route

        logging.info(f"Fetching data for route: {data_route}")

        params: Dict[str, Any] = {
            "data": data_columns
        }  # Use the dict structure for internal handling

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
        if length is not None:  # Check for None explicitly as 0 is valid
            params["length"] = length
        if offset is not None:
            params["offset"] = offset
        if output_format and output_format != "json":  # Only add 'out' if not default
            params["out"] = output_format

        # Note: _send_request will handle formatting list/dict params for the URL
        response_data = self._send_request("GET", data_route, params=params)

        # Basic check for XML format - requests lib usually handles JSON decoding
        # If XML is truly needed as raw string, _send_request needs modification
        if output_format == "xml" and isinstance(response_data, str):
            logging.warning(
                "Received XML response as string. Consider adding XML parsing."
            )
            # Potentially parse XML here or return raw string
            return {"raw_xml": response_data}  # Placeholder

        return response_data  # Return the parsed JSON by default

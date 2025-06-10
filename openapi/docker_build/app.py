from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, Response, JSONResponse
from urllib.parse import parse_qs
from dicttoxml import dicttoxml
import requests
import os
import json
import dotenv
import logging
import re
import concurrent.futures
from typing import List, Dict
from markdown_plain_text.extention import convert_to_plain_text
from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

output_path_data = "./data"
output_path_queries = "./queries"
delete_path = "./deleted_documents"
parsed_datasets_directory = './data/parsed_datasets'
template_path = "./template_ostrails.json"
processed_tools_folder = 'processed_jsonfiles_tools'
processed_datasets_folder = 'processed_jsonfiles_datasets'
basex_host = "basex-test"

data_root = "/app/data"

# Solr API
dotenv.load_dotenv()
solr_url = dotenv.get_key(".env", "SOLR_URL")
username = dotenv.get_key(".env", "USERNAME")
password = dotenv.get_key(".env", "PASSWORD")
# global cache for vocabularies
vocabs = {}
# all processed files
processed_files = {}

# title should be 67 characters with 3 dots, and description should be 297 characters with 3 dots
# title_limit: int = 67 # limit for 8 media ineo
# description_limit: int = 297 # limit for 8 media ineo
title_limit: int = 65535
description_limit: int = 65535
more_characters: str = "..."
# ID length limit
id_limit: int = 128

# base query
try:
    from base_query import base_query

    logger.info(f"base_query.py found! {base_query}")
except ImportError:
    base_query = "koninklijke bibliotheek"
    logger.info(f"base_query.py not found! Using default base query: {base_query}")

app = FastAPI()


def get_id_from_file_name(file_name: str) -> str:
    parts = file_name.split(".")[0:-1]
    parts = ".".join(parts)
    # return file_name.split(".")[0:-1].split("/")[-1]
    return parts.split("/")[-1]


def shorten_text(text: str, limit: int, more_characters: str = "...") -> str:
    """
    Shorten the text to a given limit and add more characters if the text is longer than the limit.
    """
    text = convert_to_plain_text(text)
    if text.startswith("{}"):
        text = "{code:und}" + text[2:]
    return text[:limit] + more_characters if len(text) > limit else text


def shorten_list_or_string(long_text: str | list, limit: int, more_characters: str):
    """
    Shorten the text to the given limit and add more_characters at the end.
    """
    if isinstance(long_text, list):
        shortened = [shorten_text(elem, limit, more_characters) for elem in long_text]
    elif isinstance(long_text, str):
        shortened = shorten_text(long_text, limit, more_characters)
    else:
        raise TypeError(f"Name field is not a string or a list: {type(long_text)} - {long_text}")
    return shortened


def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def _fetch_solr_records(query: str, solr_url: str, username, password, start=0, rows=10000) -> Dict:
    """
    Retrieve Solr records in parallel with a given query.
    """
    params = {
        "q": query,
        "wt": "json",
        "start": start,
        "rows": rows,
    }
    response = requests.get(f"{solr_url}/select", params=params, auth=(username, password))
    response.raise_for_status()  # Raise exception if the request failed
    data = response.json()
    return data["response"]


def fetch_solr_records(query: str, solr_url: str, username: str, password: str, start=0, rows=10000) -> List[Dict]:
    """
    Retrieve Solr records in parallel with a given query.
    """
    # Retrieve the total number of records
    response = _fetch_solr_records(query, solr_url, username, password, start=start, rows=0)
    total_records = response["numFound"]
    logger.info(f"Total records in Solr: {total_records}")

    # Retrieve the records in parallel
    records = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for start in range(0, total_records, rows):
            futures.append(
                executor.submit(
                    _fetch_solr_records, query, solr_url, username, password, start=start, rows=rows
                )
            )
        for future in concurrent.futures.as_completed(futures):
            records.extend(future.result()["docs"])
    return records


def store_solr_response(base_query: str, solr_url: str, username, password, parsed_datasets_directory: str):
    """
    Store the list of records from fetch_solr_records into individual JSON files.
    """
    """
    Saves individual datasets as separate JSON files

    Args:
    parsed_datasets_directory (str): Path to the directory to save the parsed datasets.
    dataset_file_path (str): Path to the dataset JSON file.

    """
    # Create the parsed_datasets folder if it doesn't exist
    if not os.path.exists(parsed_datasets_directory):
        os.makedirs(parsed_datasets_directory)

    # Get datasets
    logger.info(f"Getting and parsing datasets ...")
    docs: List[Dict] = fetch_solr_records(base_query, solr_url, username, password, start=0, rows=100)

    # Extract individual datasets from the 'docs' array
    for doc in docs:
        # remove HTML tags from the description field
        temp_list = []
        for elem in doc.get("description", []):
            temp_list.append(remove_html_tags(elem))
        doc["description"] = temp_list
        # shorten title and description
        doc["name"] = shorten_list_or_string(doc.get("name", ""), title_limit, more_characters)
        doc["description"] = shorten_list_or_string(doc.get("description", ""), description_limit, more_characters)

        # get the id of the dataset and shorten it to 128 characters if it is longer
        current_id: str | None = doc.get("id", None)
        if current_id is None:
            raise Exception(f"Dataset {doc} does not have 'id'!")
        if len(current_id) > id_limit:
            current_id = current_id[:id_limit]

        dataset_filename = os.path.join(parsed_datasets_directory, f"{current_id}.json")
        logger.debug(f"Saving dataset to {dataset_filename}")
        try:
            with open(dataset_filename, 'w') as dataset_file:
                json.dump(doc, dataset_file, indent=2)
        except Exception as ex:
            logger.error(f"Error saving dataset to {dataset_filename}: {ex}")
            print(doc)
            exit()


def _harvest_datasets():
    """
    This function downloads the latest datasets from the Solr API and saves them as individual JSON files.
    """
    # Get INEO records from Solr and save them as individual JSON files
    # current_path = os.path.dirname(os.path.abspath(__file__))
    store_solr_response(base_query, solr_url, username, password, parsed_datasets_directory)
    logger.debug(f"Datasets are saved in {parsed_datasets_directory}")


def create_minimal_ruc(current_id: str) -> dict:
    """
    Create a minimal RUC (Rich User Contents) object with default values.
    Used when there are no RUC files.
    The title of the minimal RUC will be overwritten by the template.json (leading codemeta.jsonl)
    Current_id (str): The identifier of the c3 codemeta.jsonl
    """
    ruc = {
        "identifier": current_id,
        "title": current_id,
    }
    return ruc


def resolve_path(ruc, path):
    """
    Function to resolve a path within a nested dictionary. It splits the path into steps, and if a step starts with "$",
    it looks for a matching key in the dictionary to access the nested values.
    """
    logger.debug(f"path[{path}]")
    steps = path.split("/")
    step = steps[0]
    logger.debug(f"step[{step}]")
    if step.startswith("$"):
        step = step.replace("$", "")
        ruc_key = step
        for key in ruc.keys():
            if key.lower() == step.lower():
                ruc_key = key
        step = ruc[ruc_key]
        logger.debug(f"$step[{step}]")
    ruc_key = None
    for key in ruc.keys():
        logger.debug(f"key[{key}]")
        if key.lower() == step.lower():
            ruc_key = key
            if len(steps) == 1:
                res = ruc[ruc_key]
                logger.debug(f"res[{res}]")
                return res
            else:
                if isinstance(ruc[ruc_key], dict):
                    res = resolve_path(ruc[ruc_key], "/".join(steps[1:]))
                    logger.debug(f"res[{res}]")
                    return res
                else:
                    logger.debug(f"path is deeper, but dict not!")
                    return None


def call_basex(query: str, host: str, port: int, user: str, password: str, action: str,
               db: str = None, content_type: str = "application/json", http_caller=requests,
               cooldown: int = 300) -> requests.Response:
    """
    This function calls the basex query

    query (str): The query to be executed
    host (str): The host of the basex server
    port (int): The port of the basex server
    user (str): The user of the basex server
    password (str): The password of the basex server

    return (str): The response of the basex query
    """
    if db:
        url: str = f"http://{user}:{password}@{host}:{port}/rest/{db}"
    else:
        url: str = f"http://{user}:{password}@{host}:{port}/rest"

    # print(f"Executing the basex query: {query} on {url=} with {action=} ...")
    # logger.info(f"Executing the basex query: {query} on {url=} with {action=} ...")
    if action == "get":
        response = http_caller.get(url, data=query, headers={"Content-Type": content_type})
    elif action == "post":
        response = http_caller.post(url, data=query, headers={"Content-Type": content_type})
    else:
        raise Exception(f"Invalid action {action}; Valid actions are 'get' and 'post'")

    return response


def call_basex_with_query(query: str,
                          host: str,
                          port: int,
                          user: str,
                          password: str,
                          action: str,
                          db: str,
                          content_type: str = "application/json",
                          http_caller=requests
                          ) -> requests.Response:
    """
    This function calls the basex query

    file_path (str): The file path to the query to be executed
    host (str): The host of the basex server
    port (int): The port of the basex server
    user (str): The user of the basex server
    password (str): The password of the basex server

    return (str): The response of the basex query
    """
    query = query.replace("<js:", "&lt;js:")
    query = query.replace("</js:", "&lt;/js:")
    query = """
    <query>
        <text>
            {query}
        </text>
    </query>
    """.format(query=query)
    response = call_basex(query, host, port, user, password, action, db, content_type, http_caller)
    return response


def checking_vocabs(value):
    """
    This function is used to modify and standardize the query results of the research activities and domains (activities.rq and domains.rq) in order to be mapped against nwo-research-fields.json
    research domains: Some namespaces in "applicationCategory" in the codemeta files need to be expanded with the correct URL (e.g. nwo:ComputationalLinguisticsandPhilology > https://w3id.org/nwo-research-fields#ComputationalLinguisticsandPhilology)
    research domains: Some values in "applicationCategory in the codemeta files contain the correct URL with "w3id.org"
    research activities: Checking if the URL contains vocabs.dariah.eu in order to be mapped to nwo-research-fields.json.

    !Further processing of the research domains and activities (checking against INEO with lowercase spellingvariations) happens in ineo-sync.py!
    value: type = 'str', the jsoniq query result of activities.rq or domains.rq.

    """
    if "nwo" in value:
        return re.sub(r'^nwo:', 'https://w3id.org/nwo-research-fields#', value)
    elif "w3id.org" in value:
        return value
    elif "vocabs.dariah.eu" in value:
        logger.debug("The value contains 'vocabs.dariah.eu'")
        return value
    elif ">" in value:
        logger.debug("Value contains '>' and will be ignored")
        return None
    else:
        return value


def prepare_basex_tables(table_name: str,
                         folder: str,
                         host: str = "basex-test",
                         port: int = 8080,
                         user: str = "admin",
                         password: str = "pass",
                         action: str = "post") -> None:
    """
    This function prepares the basex tables for the tools and datasets

    table_name (str): The name of the table to be created
    folder (str): The folder containing the json files to be inserted into the basex table

    return (None)
    """
    logger.info(f"Preparing basex table {table_name} with folder {folder} ...")
    content_type: str = "application/xml"

    content = """
    <query>
        <text><![CDATA[
    import module namespace db = "http://basex.org/modules/db";

    db:create(
      "{table_name}",
      "{folder}",
      (),
      map {{
        "createfilter": "*.json",
        "parser": "json",
        "jsonparser": "format=basic,liberal=yes,encoding=UTF-8"
      }}
    )
    ]]></text>
    </query>
    """.format(table_name=table_name, folder=folder)

    # Create the basex table
    response = call_basex(content, host, port, user, password, action, content_type=content_type)
    if 199 < response.status_code < 300:
        logger.info(f"Basex table {table_name} created with folder {folder} ...")
    else:
        logger.error(f"Failed to create the basex table {table_name} with folder {folder} ...")
        logger.error(f"Response: {response.text}")
        raise Exception(f"Failed to create the basex table {table_name} with folder {folder} ...")


def _init_basex():
    """
    # NOTE: The folder should be the path on basex container, which is mounted in docker compose file
    """
    # prepare basex tables
    # for datasets
    datasets_table_name: str = "datasets"
    prepare_basex_tables(datasets_table_name, parsed_datasets_directory)


def process_vocabs(vocabs, vocab, val):
    """
    This function compares the links of the properties (e.g. mediaType, status ) from INEO with the outcome of the jsoniq query on the codemeta files.
    To make the comparisons case-insensitive, both vocab links and val are converted to lowercase (or uppercase).

    !Further processing of the research domains and research activities (checking against INEO with lowercase spellingvariations) happens in ineo-sync.py!

    It merges the index number and title of the properties in the format {index + title} "7.23 plain"
    """

    # Check if the 'properties' key of e.g. MediaType is present in the properties
    if vocab in vocabs:
        # Iterate through the 'mediaTypes' list
        for item in vocabs[vocab]:
            # Check if val is present in the 'title'
            if val.lower() == item['title'].strip().lower():
                # If there is a match, return index and title (if the index is null (e.g. by status properties) return only the title)
                if item['index'] is not None:
                    result = f"{item['index']} {item['title'].strip()}"
                else:
                    result = f"{item['title'].strip()}"

                # vocabs_list.append(result)
                return result
        else:
            logger.debug(f"There is no match for {val}")


def retrieve_info(info, ruc, template_type: str, current_id) -> list | str | None | str:
    """

    This scripts parses and processes a set of input instructions from template.json (info, e.g. md:@queries/domains.rq:researchDomains,null)
    The function returns the result of processing these instructions (res), which could be a list, a string, or None.

    The input instruction is further split using commas as delimiters (info_values), and different components of the instruction are processed.
    This means that the order of the instruction is important: the loop is exited if a result is found.

    The instructions in the template include:
        ruc: if an instruction starts with "ruc", it indicates that the function should extract information from the Rich User Contents
            - if it starts with "ruc", the instruction is further split using colons as delimiters (info_parts), and different components of the instruction are processed.
            - such a component can include a regular expression (e.g. "<ruc:overview:^.*(### Data.*) > "^.*(### Data.*)") which further transforms the extracted data.
        md: if an instruction starts with "md", it indicates that the function should retrieve information from the codemeta.json files, potentially using a jsoniq query.
            the codemeta.json files are converted to a jsonl file that is stored in RumbleDB (done by script FAIRdatasets_tools_harvester.py)
            - if an instruction starts with "md" the info is further split into components. If a component start with "@" it indicates that there is a path to a file path containing a jsoniq query ("@queries/author.rq" > "queries/author.rq").
            - if is does not start with "@" (e.g. md:description > description) a query string is created.
            - if a query is found, the function sends a POST request to RUMBLEDB with the query and processes and filters the response.
            - component "researchactivity" or "researchdomain" ("<md:@queries/activities.rq:researchActivity > researchActivity). Extra filter to further process the response of the jsoniq query (see functions "process_vocabs" and "checking_vocabs")
        api: if an instruction starts with "api", it sets the res variable to the string "create".
        err: if an instruction starts with "err", it indicates that an error message should be printed to the standard error stream (err:there is no learn!" > there is no learn!)
        null: if an instruction starts with "null", it sets the res variable to the string "null".

    info: type  = 'str', input instruction from template.json (information after "<" in def traverse_data, e.g. md:@queries/domains.rq:researchDomains)
    ruc: type = 'dict', Rich User Contents (from Github Repository ineo-content). The ruc is processed and created in script FAIRdatasets_tools_harvester.py.
    res: type = 'str' | 'list' | None, the function returns the value stored in the res variable, which represents the result of processing the instructions in the template.

    """
    # res is the final return value of the function
    res = None

    global vocabs

    logger.info(f"info[{info}]")
    logger.error(f"info[{info}]")
    info_values = info.split(",")
    for info_value in info_values:
        logger.debug(f"info_value[{info_value}]")
        logger.error(f"info_value[{info_value}]")
        if info_value.startswith("ruc"):
            info_parts = info_value.split(":")
            logger.debug(f"info_parts[{info_parts}]")

            if len(info_parts) >= 2:
                """
                get the contents of the key in the RUC and assign it to info
                """
                template_key = info_parts[1].strip().lower()
                if template_key.endswith("[]"):
                    template_key = template_key[:-2]

                info = resolve_path(ruc, template_key)
                logger.debug(f"The value of '{template_key}' in the RUC: {info}")

            if info is not None and len(info_parts) > 2:
                regex_str = info_parts[2].strip()
                regex = re.compile(regex_str, flags=re.DOTALL)
                logger.debug(f"the regex string is: {regex_str}")
                if isinstance(info, list):
                    match = [
                        regex.search(item) if regex.search(item) is not None else item
                        for item in info
                    ]
                else:
                    match = regex.search(info)

                info: list | str | None = []
                if match is not None and isinstance(match, list):
                    for m in match:
                        if isinstance(m, str):
                            info.append(m)
                        else:
                            info.append(m.group(1))
                elif match is not None:
                    logger.debug(f"The regex value of '{regex_str}': {info}")
                    info = match.group(1)
                else:
                    logger.debug(f"The regex value of '{regex_str}': {info}")
                    info = None

            org_info = info
            if info is not None and len(info_parts) > 3:
                template_key = info_parts[1].strip().lower()
                if template_key.endswith("[]"):
                    # in case of carousel
                    text: str = ":".join(info_parts[3:])
                    text: list = [
                        text.replace("$1", i)
                        if not (i.startswith("https://") or i.startswith("http://"))
                        else i
                        for i in info
                    ]
                else:
                    # in case of string
                    text: str = info_parts[3].strip()
                    # text is changing type here to list
                    text: str = text.replace("$1", info)

                info = text
                logger.debug(f"The text value of '{info_parts[3].strip()}': {info}")

            res = info
            if res is not None:
                break  # Exit the loop once a match is found

        # With the http request method POST, the INEO api can perform three operations: create, update and delete.
        # the default option is create. This will be further processed in ineo_sync.py
        if info_value.startswith("api"):
            res = "create"

        # The default values is defined in the template after the column
        if info_value.startswith("default"):
            logger.debug(f"Starting with {info_value}")
            info_parts = info_value.split(":")
            logger.debug(f"info_parts[{info_parts}]")

            res = info_parts[1]

        # Checking if the info_value string begins with "md" (e.g. "<md:@queries/activities.rq,null")
        # First check if the JSONL file of codemeta is not empty
        if info_value.startswith("md"):
            info = None
            logger.info(f"Starting with {info_value}")
            logger.error(f"Starting with md: {info_value}")

            info_parts = info_value.split(":")
            logger.debug(f"info_parts[{info_parts}]")

            if len(info_parts) >= 2:
                path = info_parts[1]

                original_path = None
                if path.endswith("[]"):
                    original_path = path
                    path = path[:-2]  # Remove the '[]' suffix

                query = None
                file = None
                # Checking if the path starts with "@" character. If it does, it indicates that the path refers to a file path containing a query.
                if path.startswith("@"):
                    # If the path starts with "@", this line extracts the file path by removing the "@" character.
                    # For example, if path is "@queries/activities.rq", the path will be set to "queries/activities.rq".
                    file = path[1:]
                    logger.debug(f"path for the query[{file}]")
                    with open(file, "r") as file:
                        query = file.read()
                if query is not None:
                    # query = query.replace("{JSONL}", rumbledb_jsonl_path)
                    query = query.replace("{ID}", current_id)
                # This line generates a query string. It's a fallback query that is used when there is no external query file.
                else:
                    if "datasets" == template_type:
                        query = f"""
                        declare namespace js="http://www.w3.org/2005/xpath-functions";

                        for $i in js:map
                        let $ID:="{current_id}"
                         where $i/js:string[@key='id']=$ID
                         return xml-to-json($i/js:*[@key='{path}'][1])
                        """.format(current_id=current_id, path=path)
                        # query = f'for $i in json-file("{rumbledb_jsonl_path}",10) where $i.id eq "{current_id}" return $i.{path}'
                    elif "tools" == template_type:
                        query = f"""
                        declare namespace js="http://www.w3.org/2005/xpath-functions";

                        for $i in js:map
                        let $ID:="{current_id}"
                         where $i/js:string[@key='identifier']=$ID
                         return xml-to-json($i/js:*[@key='{path}'][1])
                        """.format(current_id=current_id, path=path)
                    else:
                        raise TypeError(
                            f"Invalid template type {template_type}; Valid types are 'datasets' and 'tools'")
                        # query = f'for $i in json-file("{rumbledb_jsonl_path}",10) where $i.identifier eq "{current_id}" return $i.{path}'

                logger.debug(f"basex query[{query}]")

                dbname = "datasets" if "datasets" == template_type else "tools"

                # timing the query call
                response = call_basex_with_query(query,
                                                 basex_host,
                                                 8080,
                                                 "admin",
                                                 "pass",
                                                 "post",
                                                 dbname
                                                 )
                assert (
                        response.status_code == 200
                ), f"HttpError {response.status_code} Error running {query} on basex: {response.text}"
                # check whether the query run was successful
                try:
                    if response.text is not None and len(response.text) > 0:
                        resp = json.loads(response.text)
                    else:
                        resp = None
                except json.JSONDecodeError:
                    # resp = "" + response.text
                    logger.error(f"Error running {query} on basex: {response.text}")
                    raise

                if resp is not None and len(resp) > 0:
                    if isinstance(resp, str) or isinstance(resp, list):
                        info = resp
                    else:
                        raise TypeError(f"Invalid response type {type(resp)}. Allowed types are list and str.")
                else:
                    info = None

            if info is not None and len(info_parts) > 2:
                vocab = info_parts[2].strip()
                logger.debug(f"filter on vocab[{vocab}]")

                if vocab not in vocabs.keys():
                    # Load the vocabs file to be used later
                    with open(f"/src/properties/{vocab}.json", "r") as vocabs_file:
                        vocabs[vocab] = json.load(vocabs_file)

                vocabs_list = []
                result_info = []

                for val in info:
                    checked_val = checking_vocabs(val)
                    logger.debug(vocab, val)
                    try:
                        if checked_val is not None and checked_val.startswith("https://w3id.org/nwo-research-fields#"):
                            result_info.append(checked_val)
                            info = result_info
                        else:
                            # Retrieve the index number of the title of the property for mapping to INEO. E.g. for MediaTypes that is 7.23 plain
                            info = process_vocabs(vocabs, vocab, val)
                            logger.debug(f"The vocab value from '{info_parts[2].strip()}': {val}")
                            if info is not None:
                                vocabs_list.append(info)
                            if len(vocabs_list) > 0:
                                unique_list = list(set(vocabs_list))
                                info = unique_list
                            else:
                                info = None
                    except Exception as ex:
                        logger.error(f"Error processing vocabs {info_parts} - {val}: {ex}")
                        exit("error found")

            if info is not None:
                logger.debug(f"The value of '{path}' in the MD: {info}")

            res = info
            if res is not None:
                break  # Exit the loop once a match is found

        # check for literal values
        logger.debug("### info_value: " + info_value)
        if info_value.startswith("lit#"):
            info_parts = info_value.split(":")
            logger.error(f"### info_parts[{info_parts}]")

            if len(info_parts) >= 2:
                res = info_parts[1]
                logger.error(f"Literal value ###: {res}")

        # This line checks if info_value starts with the prefix "err" ("<ruc:learn,err:there is no learn!")
        if info_value.startswith("err"):
            msg = info_value.split(":")[1].strip()  # "there is no learn!"
            # Print the error message to stderr
            logger.debug(f"error message given by template.json: [{msg}]")

        # checks if info_value starts with the prefix "null" and indicates that the result should be set to "null".
        if info_value.startswith("null"):
            logger.debug(f"Starting with 'null':{info_value}")
            # TODO FIXME: replace string "null" with None to check whether it is working
            res = None

    return res


def traverse_data(template, ruc, template_type: str, current_id):
    """
    This function traverses and processes the template.

    value: type = 'str', value of the template.json (e.g. "<md:@queries/plangs.rq,null")
    key: type = 'str', key of the template.json (e.g. "programmingLanguages")
    info: type = 'str', extracted information after "<" if the value starts with "<" (e.g. "<md:@queries/plangs.rq,null" > md:@queries/plangs.rq,null)
    """

    res = None

    logger.error(f"in travese data")
    # Check if the data is a dictionary
    if isinstance(template, dict):
        res = {}
        for key, value in template.items():
            # value is a string starting with <
            if isinstance(value, str) and value.startswith("<"):
                # Extract the information after the '<'
                info = value.split("<")[1]
                logger.error(f"curent info is {info}")
                value = retrieve_info(info, ruc, template_type, current_id)
            elif isinstance(value, str) and value.startswith("lit#"):
                info = value
                value = retrieve_info(info, ruc, template_type, current_id)
            else:
                # dealing with nested dictionaries or lists
                value = traverse_data(value, ruc, template_type, current_id)
            if value is not None:
                if value == "null":
                    res[key] = None
                else:
                    res[key] = value

    # If the data is a list
    elif isinstance(template, list):
        res = []
        for item in template:
            if isinstance(item, str) and item.startswith("<"):
                # Extract the information after the '<'
                info = item.split("<")[1]
                item = retrieve_info(info, ruc, template_type, current_id)
            else:
                # dealing nested dictionaries or lists
                item = traverse_data(item, ruc, template_type, current_id)
            if item is not None:
                if item == "null":
                    res.append(None)
                else:
                    res.append(item)
    return res


def template(current_id: str, template_path: str, template_type: str = "datasets"):
    """
    Main function

    This script processes JSON data using a template (template.json) and retrieving information from it based on a set of instructions defined in template.py.
    This function starts the process of traversing the template and retrieving the information from the Rich User Contents (RUC) and codemeta files (MD)
    then merge them into an INEO json file to ultimately feed into the INEO API.

    template: type = 'dict', the template file loaded as json, by default it is always a list of dictionaries as INEO supports multiple records
    ruc: type = 'dict', the rich user contents file loaded as json, by default it is always a dictionary as it contains only one record
    res: type = 'list', the result of combining the RUC and the MD based on the instructions set out in template.py.

    """
    logger.debug(f"### Processing {current_id} of type {template_type} with {template_path}")
    # DSL template
    # global template
    logger.error(f"template_path: {template_path}")
    with open(template_path, "r") as file:
        template = json.load(file)

    # Rich User Contents
    ruc = None

    # Load RUC dictionary or create a minimal RUC object if not existent
    ruc_file_path = f"./data/rich_user_contents/{current_id}.json"

    if os.path.exists(ruc_file_path):
        with open(ruc_file_path, "r") as json_file:
            ruc = json.load(json_file)
        logger.debug(f"RUC contents: {ruc}")
    else:
        ruc = create_minimal_ruc(current_id)

    # Combine codemeta/datasets and RUC using the template
    logger.error(f"current id {current_id}")
    res = traverse_data(template, ruc, template_type, current_id)

    # Create folders if they don't exist
    tools_folder = processed_tools_folder
    datasets_folder = processed_datasets_folder

    if not os.path.exists(tools_folder):
        os.makedirs(tools_folder)

    if not os.path.exists(datasets_folder):
        os.makedirs(datasets_folder)

    logger.error(f"Processing result: {res} of type {type(res)}")
    folder_name = datasets_folder

    filename = os.path.join(folder_name, f"{current_id}_processed.json")

    with open(filename, 'w') as file:
        json.dump(res, file, indent=2)

    logger.info(f"JSON files saved successfully. {filename}")


def get_accept_header(accept: str | None):
    if accept is None:
        accept_header = "application/json"
    else:
        query_params = parse_qs(accept)
        accept_header = query_params.get('accept', None)
        if accept_header:
            accept_header = accept_header[0]
        else:
            accept_header = "application/json"
    return accept_header


def create_response(data: dict | None, accept: str):
    data = data or {}
    if accept == "application/xml":
        xml_response = dicttoxml(data)
        return Response(content=xml_response, media_type="application/xml")
    elif accept == "text/plain":
        plain_text_response = "\n".join([f"{key}: {value}" for key, value in data.items()])
        return Response(content=plain_text_response, media_type="text/plain")
    else:
        return JSONResponse(content=data)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return "<h1>Hello, World!</h1><p>Example: <a href='/products/test.json'>/products/test.json</a></p>"


# @app.get("/validate/{file_path}")
@app.get("/{type_path}/{file_path}")
async def get_file(type_path: str, file_path: str, accept: str | None = Query(None)):
    logger.warning(f"type_path: {type_path}")
    logger.warning(f"original file_path: {file_path}")
    filename = os.path.basename(file_path)
    logger.warning(f"filename basename: {filename}")
    file_path = os.path.join(data_root, type_path, filename)
    logger.warning(f"file_path: {file_path}")
    accept_header = get_accept_header(accept)
    if os.path.isfile(file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
        return create_response(data, accept_header)
    else:
        return JSONResponse(content={"error": f"File not found {file_path}"}, status_code=404)


# @app.get("/products/{product_id}")
# async def get_product(product_id: str, accept: str | None = Query(None)):
#     global processed_files
#     accept_header = get_accept_header(accept)
#
#     if len(processed_files) == 0:
#         processed_files = load_files(processed_datasets_folder)
#
#     if product_id == "random":
#         product_id = random.choice(list(processed_files.keys()))
#     elif not product_id.endswith("_processed"):
#         product_id = f"{product_id}_processed"
#     v: list = processed_files.get(product_id, [])
#
#     logger.error(f"result is {v}")
#     return create_response(v, accept_header)


# @app.get("/products")
# async def get_products(accept: str | None = Query(None)):
#     global processed_files
#     accept_header = get_accept_header(accept)
#
#     if len(processed_files) == 0:
#         processed_files = load_files(processed_datasets_folder)
#     k, v = next(iter(processed_files.items()))
#     logger.error(f"Returning {k} - {v}")
#
#     return create_response({"accept": accept_header, "total": len(processed_files), k: v}, accept_header)


@app.get("/{type_path}")
async def get_items_per_type(type_path: str, accept: str | None = Query(None)):
    """
    Get all items of a specific type (datasets or tools).
    """
    accept_header = get_accept_header(accept)

    items = load_files(os.path.join(data_root, type_path))

    return create_response({"accept": accept_header, "total": len(items), "items": items}, accept_header)


@app.get("/fetchall", response_class=HTMLResponse)
async def fetch_all():
    # harvest datasets
    logger.info("Harvesting datasets ...")
    try:
        _harvest_datasets()
    except Exception as ex:
        logger.error(f"Failed to harvest datasets: {ex}")
        return HTMLResponse(content="<h1>Failed to harvest datasets<h1>", status_code=500)
    return HTMLResponse(content="<h1>Fetched records from solr<h1>", status_code=200)


def load_files(directory: str, file_type: str = "json") -> Dict:
    """
    Load files from a directory and return a dictionary with the file content.
    """
    files = {}
    for file_name in os.listdir(directory):
        if file_name.endswith(f".{file_type}"):
            with open(os.path.join(directory, file_name), "r") as file:
                file_id = get_id_from_file_name(file_name)
                files[file_id] = json.load(file)
    return files


@app.get("/initdb", response_class=HTMLResponse)
def init_db():
    # initialize basex
    logger.info("Initializing basex ...")
    try:
        _init_basex()
    except Exception as ex:
        logger.error(f"Failed to initialize basex: {ex}")
        return HTMLResponse(content="<h1>Failed to initialize basex<h1>", status_code=500)
    return HTMLResponse(content="<h1>Initialized basex<h1>", status_code=200)


@app.get("/transform", response_class=HTMLResponse)
async def transform():
    # transform records
    logger.info("Transforming datasets ...")
    ineo_records = load_files(parsed_datasets_directory)  # {id: location}

    for current_id in tqdm(ineo_records.keys()):
        template(current_id, template_path, "datasets")

    return HTMLResponse(content="<h1>Transformed records<h1>", status_code=200)

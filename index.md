---
title: API Specification
layout: default
nav_order: 6
---

# API Specifications

{: .highlight }

## Versions

**OpenAPI** is used to describe the endpoints and the format of the objects to exchange on the wire, the specifications are shared below.

* The current (i.e., last) version of the SKG-IF OpenAPI specifications is available at [https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://w3id.org/skg-if/api/skg-if-openapi.yaml).
* One can access the OpenAPI specifications of all (current and previous) versions by using a version number in the `w3id.org` URL, following this pattern:
`https://w3id.org/skg-if/api/<X.Y.Z>/skg-if-openapi.yaml`.


The SKG-IF OpenAPI version, present in the YAML, is independent from the SKG-IF Data model version.

Please also refer to the [SKG-IF OpenAPI Implementer documentation](https://docs.google.com/document/d/1t7b7h28UTtM56Sda4NGJIp0hnQfGbcVVGn12fny9wfI/edit?tab=t.0#heading=h.hso3muyqtlhx). You will find detailed information to validate your API implementation.

## Versions history

| SKG-IF OpenAPI | SKG-IF OpenAPI YAML | SKG-IF compatible data model |
| ----- | ----- | ----- |
| 1.0.0 (Current) | `https://w3id.org/skg-if/api/skg-if-openapi.yaml` | 1.1.0 |


### Current context

``` yaml
openapi: 3.1.0
info:
  version: 1.0.0
  title: SKG-IF OpenAPI - compatible with SKG-IF Data Model 1.1.0

  ...
   "@context":
    "https://w3id.org/skg-if/context/1.1.0/skg-if.json", // Fixed SKG-IF data model context
    "https://w3id.org/skg-if/context/1.0.0/skg-if-api.json", // Fixed SKG-IF API context
    {
      "@base": "https://w3id.org/skg-if/sandbox/acme/"
    }
  ...

```

Make sure your server JSON-LD output implementation is using the same context JSON URLs, refer to paragraph below to define your `@base`.


## OpenAPI viewers

You can also visualize the OpenAPI specifications with standard tools like :

* Stoplight : [https://elements-demo.stoplight.io/?spec=https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://elements-demo.stoplight.io/?spec=https://w3id.org/skg-if/api/skg-if-openapi.yaml)
* Swagger : [https://editor.swagger.io/?url=https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://editor.swagger.io/?url=https://w3id.org/skg-if/api/skg-if-openapi.yaml)


## Define your @base and local_identifier format

* `local_identifier` act as a persistent identifier, PID stable URL. `local_identifier` is an alias of JSON-LD `@id`.
* `@base` is a default HTTP prefix fallback for all identifiers not defined as URLs in the `@graph`. In JSON-LD, an `@id` value, when not starting with “http”, is interpreted by concatenation to the `@base` (refer to RFC 3986 relative IRI resolution).

You have a few options, to define your `local_identifier` format for your ACME organisation.

* __Option 1__: Define a [w3id.org](https://w3id.org) domain ex: `https://w3id.org/acme/`. You can set up w3id.org to redirect to your catalogue. ex: `https://w3id.org/acme/prod-1` => `https://www.acme.com/product-catalogue/prod-1`. This approach is a flexible way to define PIDs for your entities.
  * `@base`: `https://w3id.org/acme/`
  * Product `local_identifier` JSON value example : `https://w3id.org/acme/prod-1` or `prod-1`
* __Option 2__: If you mint DOIs for your main entities you expose (typically the research products), you can use the DOI itself as `local_identifier`. Use a full DOI URL in the `local_identifier` value. Use w3id.org SKG-IF sandbox as `@base`.
  * `@base`: `https://w3id.org/skg-if/sandbox/acme/`
  * Product `local_identifier` JSON value example : `https://doi.org/10.1234/56789` (full DOI URL)
* __Option 3__: Use an existing dedicated domain ex: `https://www.acme.com/graph/`. It is a best practice that this URL is dereferenceable, in a human readable format.
  * `@base`: `https://www.acme.com/graph/`
  * Product local_identifier JSON value example : `https://www.acme.com/graph/prod-1` or `prod-1`
* __Option 4__: Use `https://w3id.org/skg-if/sandbox/acme/` for all entities. Note, these URLs will not be dereferenceable.
  * `@base`: `https://w3id.org/skg-if/sandbox/acme/`
  * Product `local_identifier` JSON value example : `https://w3id.org/skg-if/sandbox/acme/prod-1` or `prod-1`
  * _You can use Option 4 for your initial implementation iteration_

Make sure that you generate distinct URLs for person, product... They should not conflict.

> If you don't have stable ids for specific entity types ( typically for persons or organisations),  please refer to otf, [_on-the-fly_](https://skg-if.github.io/interoperability-framework/#local-identifiers-of-entities) ids.

> __Important__ : You cannot use the SKG-IF API root URL itself as the `@base`. It is an SKG-IF design choice to keep the entity identifiers completely separated from the SKG-IF API. To see how the API URL and `local_identifier` are associated for entity resolution, refer below [entity resolving](#api-get-entity-by-id-single-entity-resolving).

## Endpoints and JSON-LD output

* The SKG-IF OpenAPI defines 2 types of endpoints
  * Get _Entity_ by Id
  * Get List of _Entity_
* The SKG-IF OpenAPI endpoints outputs are JSON-LD and compatible with the [SKG-IF data model](https://skg-if.github.io/interoperability-framework/)

You can refer to [static json-ld examples] (https://github.com/skg-if/api/tree/main/openapi/ver/current/sample_data).
 
## API Get Entity by Id, single entity resolving

Single entity resolve API format follows this format `https://acme.com/skg-if/api/{entity-type}/{local_identifier}`.

* Your API _MUST_ be able to resolve full local_identifiers as URL.
  * Example: `https://acme.com/skg-if/api/products/https://w3id.org/skg-if/sandbox/acme/prod-1`
* Your API _SHOULD_ be able to resolve local_identifier without prefix.
  * Example: `https://acme.com/skg-if/api/products/prod-1`

> Note : this pattern is also used in standard SKG proprietary APIs like Crossref
> * [http://api.crossref.org/works/https://doi.org/10.1039/d1cb00160d](http://api.crossref.org/works/https://doi.org/10.1039/d1cb00160d) => resolve OK
> * [http://api.crossref.org/works/10.1039/d1cb00160d](http://api.crossref.org/works/10.1039/d1cb00160d) => resolve OK

## API links

* The `@graph` array contains entities, identified by their `local_identifier`, each entity may have relation to other entities also identified by their `local_identifier`.
* From a client perspective, if the sub entity is not embedded with its fields, you may need to perform sub queries to access these fields. As a client you should be able to get sub entity API links automatically when necessary, ( [HATEOAS](https://en.wikipedia.org/wiki/HATEOAS) pattern ) .
* The JSON-LD output contains a `meta` section. The `meta.api_items` SHOULD provide the API links for each sub entity identified by its `local_identifier`.


Get Product by Id : `https://acme.com/skg-if/api/products/prod-1`

``` json
{
    "meta" : {
        "local_identifier": "https://acme.com/skg-if/api/products/prod-1", // parent entity - product : API URL
        "entity_type": "single_entity",
        "api_items": [
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1", // child entity - person : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/persons/pers-1" // child entity - person : API link
                        }
                    ]
            }
            // note : The SKG-IF API link for the parent entity - product is already defined by the meta.local_identifier.
            //   You are free to duplicate it in the api_items array.
        ]
    },
    "@graph": [
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", //  parent entity - product : local_identifier / PID
            "contributions": [
            {
                "by" : {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1" // child entity - person : local_identifier / PID
                    //...
                }
                //...
            }
            ]
            //...
        }
    ]
}
```

Get List of Product : `https://acme.com/skg-if/api/products?filter=xxx&page=1`

``` json
{
    "meta": {
        "local_identifier": "https://acme.com/skg-if/api/products?filter=xxx&page=1", // search identifier, API link
        "entity_type": "single_entity",
        "api_items": [
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", // search result 1 - parent entity - product : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/products/prod-1" //  search result 1 - parent entity - product : API link
                        }
                    ]
            },
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1", // search result 1 - child entity - person : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/persons/pers-1" //  search result 1 - child entity - person : API link
                        }
                    ]
            },
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-2", // search result 2 - parent entity - product : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/products/prod-2" //  search result 2 - parent entity - product : API link
                        }
                    ]
            },
        ]

    },
    "@graph": [
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", // search result 1 - parent entity - product : local_identifier / PID
            "contributions": [
            {
                "by" : {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1" // search result 1 - child entity - person : local_identifier / PID
                    //...
                }
                //...
            }
            ]
            //...
        },
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-2" // search result 2 - parent entity - product : local_identifier / PID
            //...
        },

    ]
}

```


## Content negotiation

If you simply need to expose single entities without any API, you can expose SKG-IF with content-negotiation

The Accept header is `application/vnd.skgif.ld+json`

``` text
curl --location --request GET 'https://acme.com/skg-if/api/products/prod-1' --header 'Accept: application/vnd.skgif.ld+json'​
```


## API links - custom

You may have custom non SKG-IF API for your entities, they can be integrated in the `meta.api_links` array, with the `rel` : service.
SKG-IF Link entity relies on active stream vocabulary, rel : [https://www.w3.org/TR/activitystreams-vocabulary/#dfn-rel](https://www.w3.org/TR/activitystreams-vocabulary/#dfn-rel)

``` json
    "api_items": [
    {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", //  product : local_identifier / PID
            "urls": [
                {
                    "entity_type": "link",
                    "rel": "service",
                    "media_type": "text/xml",
                    "href": "https://acme.com/myapi/prod-1" //  product : NON SKG-IF API link
                },
                 {
                    "entity_type": "link",
                    "rel": "service",
                    "media_type": "application/json",
                    "href": "myprotocol://acme.com/serv/prod-1" //  product : NON SKG-IF API link
                },

            ]
    },
```

##  Validate a server implementation compliance with the SKG-IF OpenAPI specification.

* To validate a live implementation server see : [.github/WORFLOW.md](https://github.com/skg-if/api/blob/main/.github/WORFLOW.md)

##  Search filter formats

###  Filter format identifier ids

On this the get list of entity URLs like `https://acme.com/skg-if/api/products?filter=identifiers.id:xxx&page=1`.
You may wonder what is the supported format for `xxx` identifiers ids.

| Simple identifier | URL identifier |
| ----- | ----- |
| 10.1609/icwsm.v15i1.18053  |  https://doi.org/10.1609/icwsm.v15i1.18053 |
| 0000-0002-5355-2576 | https://orcid.org/0000-0002-5355-2576 |

For external identifiers like DOIs, Orcids, the server :
* MUST support simple identifiers
* SHOULD support URL identifiers.

See how existing APIs support these patterns.

| Query | SKG-IF Query | Equiv. Query OpenAlex | Equiv. Query Crossref | Equiv. Query OpenAIRE |
| ----- | ----- | ----- | ----- | ----- |
| simple identifier | `products?filter=identifiers.id:10.1609/icwsm.v15i1.18053` | https://api.openalex.org/works?filter=doi:10.1609/icwsm.v15i1.18053 | https://api.crossref.org/works?filter=doi:10.1039/d1cb00160d  | https://api.openaire.eu/graph/v1/researchProducts?pid=10.1038/s41563-023-01669-z|
| simple identifier escaped | `products?filter=identifiers.id:10.1609%2Ficwsm.v15i1.18053` | https://api.openalex.org/works?filter=doi:10.1609%2Ficwsm.v15i1.18053  | https://api.crossref.org/works?filter=doi:10.1039%2Fd1cb00160d | https://api.openaire.eu/graph/v1/researchProducts?pid=10.1038%2Fs41563-023-01669-z |
| URL identifier | `products?filter=identifiers.id:https%3A%2F%2Fdoi.org%2F10.1609%2Ficwsm.v15i1.18053` | https://api.openalex.org/works?filter=doi:https%3A%2F%2Fdoi.org%2F10.1609%2Ficwsm.v15i1.18053  | https://api.crossref.org/works?filter=doi:https%3A%2F%2Fdoi.org%2F10.1609%2Ficwsm.v15i1.18053  | _https://api.openaire.eu/graph/v1/researchProducts?pid=https%3A%2F%2Fdoi.org%2F10.1609%2Ficwsm.v15i1.18053_ KO |
| URL identifier escaped | `products?filter=identifiers.id:https://doi.org/10.1609/icwsm.v15i1.18053` | https://api.openalex.org/works?filter=doi:https://doi.org/10.1609/icwsm.v15i1.18053  | https://api.crossref.org/works?filter=doi:https://doi.org/10.1039/d1cb00160d  | _https://api.openaire.eu/graph/v1/researchProducts?pid=http://doi.org/10.1038/s41563-023-01669-z_ KO|


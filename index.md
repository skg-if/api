---
title: API Specification
layout: default
nav_order: 6
---

# API Specifications

{: .highlight }

## Versions

**OpenAPI** is used to describe the endpoints and the format of the objects to exchange on the wire, the specifications are shared below.
For the sake of completeness, you can also check the [SKG-IF OpenAPI Implementer documentation](https://docs.google.com/document/d/1t7b7h28UTtM56Sda4NGJIp0hnQfGbcVVGn12fny9wfI/edit?tab=t.0#heading=h.hso3muyqtlhx).

* The current (i.e., last) version of the SKG-IF OpenAPI specifications is available at [https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://w3id.org/skg-if/api/skg-if-openapi.yaml).
* One can access the OpenAPI specifications of all (current and previous) versions by using a version number in the `w3id.org` URL, following this pattern:
`https://w3id.org/skg-if/api/<X.Y.Z>/skg-if-openapi.yaml`. For instance: `https://w3id.org/skg-if/api/1.0.0/skg-if-openapi.yaml` allows to access to version 1.0.0 of the SKG-IF OpenAPI specifications.


The SKG-IF OpenAPI version, present in the YAML, is independent from the SKG-IF Data model version.

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

## Viewers

You can also visualize the OpenAPI specifications with standard tools like :

* Stoplight : [https://elements-demo.stoplight.io/?spec=https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://elements-demo.stoplight.io/?spec=https://w3id.org/skg-if/api/skg-if-openapi.yaml)
* Swagger : [https://editor.swagger.io/?url=https://w3id.org/skg-if/api/skg-if-openapi.yaml](https://editor.swagger.io/?url=https://w3id.org/skg-if/api/skg-if-openapi.yaml)


## Define your @base

`@base` is a default prefix domain fallback for all identifiers not defined as URLs in the `@graph`
A `local_identifier` value, when not starting with “http”, is interpreted by concatenation to the `@base`.

For the `local_identifier` domain (your `@base`), you have a few options for the ACME organisation.

* Use `https://w3id.org/skg-if/sandbox/acme/` . We don’t recommend it for prod because it does not resolve anywhere ( related to the ACME organisation )
* Define a [w3id.org](https://w3id.org) domain ex: `https://w3id.org/acme/` . You can set up w3id.org to redirect to your catalogue. ex: `https://w3id.org/acme/prod-1` => `https://www.acme.com/product-catalogue/prod-1`
* Use a graph dedicated domain you already have ex: `https://www.acme.com/theskg/`, `https://www.acme.com/theprodgraph/`

Make sure that you generate distinct URLs ids for person, product... They should not conflict.

## Endpoints and JSON-LD output

* The SKG-IF OpenAPI defines 2 types of endpoints
  * Get _Entity_ by Id
  * Get List of _Entity_
* The SKG-IF OpenAPI endpoints outputs are JSON-LD and compatible with the [SKG-IF data model](https://skg-if.github.io/interoperability-framework/)

## API links

* The `@graph` array contains entities, identified by their `local_identifier`, each entity may have relation to other entities also identified by their `local_identifier`.
* From a client perspective, if the sub entity is not embedded with its fields, you may need to perform sub queries to access these fields.
* The JSON-LD output contains a `meta` section SHOULD provide you API links for each entity, identified by its `local_identifier`. As a client you are not supposed to guess the API URL from the `local_identifier` format, there is no standard for the API domain prefix, each implementer is free to have a domain for its `local_identifier` and another one for its API (It is even recommended).


Get Product by Id : `https://acme.com/skg-if/api/products/prod-1`

``` json
{
    "meta" : {
        "local_identifier": "https://acme.com/skg-if/api/products/prod-1", // parent entity : API URL
        "entity_type": "single_entity",
        "api_items": [
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1", // child entity : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/persons/pers-1" // child entity : API link
                        }
                    ]
            }
        ]
    },
    "@graph": [
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", //  parent entity : local_identifier / PID
            "contributions": [
            {
                "by" : {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1" // child entity : local_identifier / PID
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
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", // search result 1 - parent entity : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/products/prod-1" //  search result 1 - parent entity : API link
                        }
                    ]
            },
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1", // search result 1 - child entity : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/persons/pers-1" //  search result 1 - child entity : API link
                        }
                    ]
            },
            {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-2", // search result 2 - parent entity : local_identifier / PID
                    "urls": [
                        {
                            "entity_type": "link",
                            "rel": "self",
                            "href": "https://acme.com/skg-if/api/products/prod-2" //  search result 2 - parent entity : API link
                        }
                    ]
            },
        ]

    },
    "@graph": [
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-1", // search result 1 - parent entity : local_identifier / PID
            "contributions": [
            {
                "by" : {
                    "local_identifier": "https://w3id.org/skg-if/sandbox/acme/pers-1" // search result 1 - child entity : local_identifier / PID
                    //...
                }
                //...
            }
            ]
            //...
        },
        {
            "local_identifier": "https://w3id.org/skg-if/sandbox/acme/prod-2" // search result 2 - parent  entity : local_identifier / PID
            //...
        },

    ]
}

```


## API Get Entity by Id, single entity resolving

Single entity resolve API format follows this format `https://acme.com/skg-if/api/{entity-type}/{local_identifier}`

For example : `https://acme.com/skg-if/api/products/prod-1`

Your API _MUST_ also be able to resolve full local_identifiers including the domain/base :

`https://acme.com/skg-if/api/products/https://w3id.org/skg-if/sandbox/acme/prod-1`


Note : this pattern is also used in standard SKG API like Crossref

* http://api.crossref.org/works/https://doi.org/10.1039/d1cb00160d => OK
* http://api.crossref.org/works/10.1039/d1cb00160d => OK






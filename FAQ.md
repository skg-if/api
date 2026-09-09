---
title: API
parent: FAQs
layout: default
nav_order: 2
---

# FAQs: API

## There is a problem on the OpenAPI specifications

* Please open a ticket on https://github.com/skg-if/api/

## Where are the JSON-LD standard @id and @type ?

* local_identifier and entity_type are alias is defined in context

https://w3id.org/skg-if/context/skg-if.json

``` json
 "local_identifier": "@id",

 "entity_type": {
      "@id": "@type",
      "@type": "@vocab"
    },

 ```

## Must I embed Agent (person) entities in the products/{local_identifier} operation OpenAPI response ?

Multiple outputs are actually possible and compatible with JSON-LD  (embed, link an id)

The SKG-IF OpenAPI provides one JSON format representation with embedded entities. This allows, with a single call, to retrieve for example : a product along with its authors and its journal (Venue), like we have in standard JSON APIs ( crossref, openalex, openaire, datacite etc…). This is only a choice for “convenient” usage of the API. We suggest you use this output
However, you can also just use an id and not an embedded the entity.

## How identifier schemes (ROR, DOI, ORCID …) are defined ?

* Identifiers are defined, in the json-ld context. ( see : https://github.com/skg-if/interoperability-framework/issues/17)
* What are options if a scheme I need is missing ?
  * You may use the generic `url` scheme. or `urn` (ok for OAI-PMH ids).
  * See also : https://github.com/skg-if/interoperability-framework/issues/36


## How can I include a specific product sub type ?

* Use manifestation type :https://skg-if.github.io/interoperability-framework/docs/research-product.html#manifestations

Example is :

 ``` json
{
    "type": {
    "class": "http://purl.org/spar/fabio/Preprint",
    "labels": {
            "en": "preprint"
    },
    "defined_in": "http://purl.org/spar/fabio”
}
```

## How can I integrate an agent entity with the API

* The `agent` entity is present in the /products operations in the field `contributions.by`
* The `agent` can also be implemented with organisations/ and persons/ operations.
* There is no agents/ operation


## My system does not have permanent local_identifiers for organisations and persons. What can I do ?

* Use on-the-fly identifiers identifiers : https://skg-if.github.io/interoperability-framework/#local-identifiers-of-entities

## Should I implement all search filters ?

* No implement only the filters you can.

* Each filter implementation is optional. If the operation does not implement one of the requested filters it must return an HTTP 422 response. see “Get list of products” operation documentation.

## When should an operation return HTTP 200 vs HTTP 404 ?

* Return HTTP 200 if the operation has a JSON-LD representation of the requested resource(s), i.e. the `@graph` field contains at least one entity.
* Return HTTP 404 otherwise.  `@graph` is then an empty array. This applies **both** to single-entity "get by id" operations (e.g. `products/{local_identifier}`) when the id does not resolve, and to "get list" / search operations (e.g. `products`) when no entity matches the given filter.

## Is content-negotiation supported by SKG-IF ?

* yes : application/vnd.skgif.ld+json
* See : https://skg-if.github.io/api/


## What is the naming convention for search filters ?

* attribute filters : data model fields structure separated with dot.
* convenient filters : "cf." prefix.

## How can I validate that my local server implementation is compliant with the SKG-IF OpenAPI ?

* See [.github/WORFLOW.md](https://github.com/skg-if/api/blob/main/.github/WORFLOW.md)


## How to extend the API for a model extension ?

* See https://skg-if.github.io/extensions/
* Example API extension for the RA-SKG extension  https://skg-if.github.io/ext-ra-skg/api/api.html  (OpenAPI overlay and speakeasy)


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

* In the json-ld context. see : https://github.com/skg-if/interoperability-framework/issues/17 (scheme update)
* What are options if a scheme I need is missing ? https://github.com/skg-if/interoperability-framework/issues/36


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

## Is content-negotiation supported by SKG-IF ?

* yes : application/vnd.skgif.ld+json
* See : https://skg-if.github.io/api/


## What is the naming convention for search filters ?

* attribute filters : data model fields structure separated with dot.
* convenient filters : "cf." prefix.

## How can I validate that my local server implementation is compliant with the SKG-IF OpenAPI ?

* See : https://docs.google.com/document/d/1t7b7h28UTtM56Sda4NGJIp0hnQfGbcVVGn12fny9wfI/edit?tab=t.0
* Read the “validation process” and “hackathon” paragraphs at the beginning of this document.
* You can include the PRISM proxy server in your CI/CD pipeline.


## How to extend the API for a model extension ?

* See https://skg-if.github.io/extensions/
* Example API extension for the RA-SKG extension  https://skg-if.github.io/ext-ra-skg/api/api.html  (OpenAPI overlay and speakeasy)


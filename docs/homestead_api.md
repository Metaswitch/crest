Homestead - API Guide
=================

Homestead provides a RESTful API. This is used by the Ellis and Sprout components.
All access must go via this API, rather than directly to the database.

Credentials
===========

    /credentials/<private ID>/<public ID>/digest

Make a GET request to this endpoint to retrieve the credentials for the specified public and private id.

Response:

* 200 if the credentials are found, returned as JSON:

    ```
    { "digest": "<DIGEST>" }
    ```

* 404 if no credentials are found

Make a POST request to this endpoint to create new credentials. Pass in the digest, in the body as JSON:

```
{ "digest": "<DIGEST>" }
```

Response:

* 200 if the credentials were succesfully created

Make a DELETE request to this endpoint to delete the credentials.

Response:

* 204 if the document was succesfully deleted (returned even if document did not exist)

Private Credentials
===================

    /privatecredentials/<private ID>/digest

Make a GET request to this endpoint to retrieve the credentials for the specified private id.

Response:

* 200 if the credentials are found, returned as JSON:

    ```
    { "digest": "<DIGEST>" }
    ```

* 404 if no credentials are found

Initial Filter Criteria
=======================

    /filtercriteria/<public ID>

Make a GET request to this endpoint to retrieve the iFCs for the specified public id.

Response:

* 200 if the iFCs are found, with the iFC XML document as the body
* 404 if no iFCs are found

Make a PUT request to this endpoint to update (or create) the iFCs for the specified public id.

Response:

* 200 if the iFCs were successfully created

Make a DELETE request to this endpoint to delete the iFCs for the specified public id.

Response:

* 204 if the iFCs were successfully deleted (returned even if document did not exist)

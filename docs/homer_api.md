Homer - API Guide
=================

Homer provides a RESTful API. This is used by the Ellis and Sprout components. 
All access must go via this API, rather than directly to the database.

Simservs documents
==================

    /org.etsi.ngn.simservs/users/<USER>/simservs.xml

Make a GET request to this endpoint to retrieve the `simservs.xml` document
for the specified USER. 

Response:

* 200 if the document is found, with the XML document as the body
* 404 if the document was not found

Make a PUT request to this endpoint to update (or create) the document for
the specified USER. 

Response:

* 200 if the document was successfully updated
* 400 if the document did not pass XSD validation, with the error in the body

Make a DELETE request to this endpoint to delete the document for
the specified USER. 

Response:

* 204 if the document was successfully deleted (returned even if document did not exist)

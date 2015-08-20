# Homestead-prov - API Guide

Homestead-prov provides a RESTful API. This is used by the Ellis component to create/delete/query subscribers. It shouldn't be used if the deployment uses a real HSS. 

All access must go via this API, rather than directly to the database. 

## Liveness checking

    /ping

Make a GET request to this endpoint to check whether Homestead-prov is running. It will return 200 OK if so.

## IMPI

    /impi/<private ID>/digest

Make a GET request to this URL to retrieve the digest of the specified private ID

The URL takes an optional query parameter: `public_id=<public_id>` If specified a digest is only returned if the private ID is able to authenticate the public ID.

Response:

* 200 if the digest is found, returned as JSON: `{ "digest_ha1": "<DIGEST>" }`
* 404 if the digest is not found.

## IMPU

    /impu/<public ID>

Make a GET request to this URL to retrieve the IMS subscription document for this public ID

Response:

* 200 if the public ID is found, returned as an IMSSubscription XML document, e.g.:

    <IMSSubscription>
        <PrivateID>...</PrivateID>
        <ServiceProfile>
            <InitialFilterCriteria>
                <TriggerPoint>...</SPT></TriggerPoint>
                <ApplicationServer>
                    <ServerName>...</ServerName>
                </ApplicationServer>
            </InitialFilterCriteria>
            <PublicIdentity>
                <Identity>...</Identity>
            </PublicIdentity>
        </ServiceProfile>
    </IMSSubscription>

* 404 if the public ID is not found.

## Private ID

    /private/<private ID>

Make a PUT to this URL to create a new private ID or update an existing one. The private ID will store the digest of the subscriber's password, and it can optinally store the subscriber's password in plaintext as well.

The PUT request has a mandatory JSON body which has the format:

    { "digest_ha1": "<DIGEST>" [, "realm": "<REALM>"] }

or

    { "plaintext_password": "<PLAINTEXT_PASSWORD>" [, "realm": "<REALM>"] }

If `digest_ha1` is used, Homestead-prov will store this digest in the Private ID (note, this is the recommended method).
If `plaintext_password` is used, Homestead-prov will calculate the digest from the password, and store the digest and the password (in plain text) in the Private ID. This option is available for RCS integration (and ease-of-use for testing), but this is less secure and so should not be used unless you particularly need it.
If the realm is omitted, homestead-prov defaults it to the configured home domain.

Response:

* 200 if the private ID was created/updated successfully.
* 400 if the body of the request is invalid

If an existing private ID has stored the subscriber's password in plaintext, but it's then updated using `digest_ha1` call, then the password is deleted from the Private ID.

Make a GET to this URL to retrieve details for a private ID. Response:

* 200 if the private ID was found, returned as JSON:

    { "digest_ha1": "<DIGEST>", "plaintext_password": "<PLAINTEXT_PASSWORD>", "realm": "<REALM>" }

  The `plaintext_password` value is only included if the subscriber was provisioned in a way to store the plaintext password.
* 404 if the private ID was not found.

Make a DELETE to this URL to delete an existing private ID. Response:

* 200 if the private ID was deleted successfully.
* 204 if the private ID could not be found.

    `/private/<private id>/associated_implicit_registration_sets/`

Make a GET to this URL to retrieve the IRSs that this private ID is configured to authenticate. Response:

* 200 if the private ID was found, returned as JSON: `{ "associated_implicit_registration_sets": ["<irs-uuid-1>", "<irs_uuid-2>"] }`
* 404 if the private ID could not be found.

    `/private/<private id>/associated_implicit_registration_sets/<irs-uuid>`

Make a PUT to this URL to configure the private ID to authenticate the specified IRS. Response:

* 200 if the private ID has been updated to authenticate the IRS.
* 404 if the private ID could not be found.

Make a DELETE to this URL to configure the private ID to no longer authenticate the specified IRS. Response:

* 200 if the private ID has been updated to _not_ authenticate the IRS.
* 204 if the private ID could not be found.

    `/private/<private ID>/associated_public_ids`

Make a GET to this URL to list the public IDs that the private ID can authenticate. Response:

* 200 if the private ID could be found, returned as JSON: `{ "associated_public_ids": ["<public-id-1>", "<public-id-2>"] }`
* 404 if the private ID could not be found.

## Implicit Registration Sets

    /irs

Make a POST to this URL to create a new IRS. Response:

* 201, with the URL of the IRS in the Location header: `Location: <irs-uuid-1>`

    `/irs/<irs-uuid>`

Make a DELETE to this URL to delete an existing IRS. Response:

* 200 if the IRS has been deleted.
* 204 if the IRS could not be found.

    `/irs/<irs-uuid>/public_ids`

Make a GET to this URL to list all the public IDs that are part of this IRS. Response:

* 200 if the IRS exists, returned as JSON: `{ "public_ids": ["<public-id-1>", "<public-id-2>"] }`
* 404 if the IRS does not exist.

    `/irs/<irs-uuid>/private_ids`

Make a GET to this URL to list all the private IDs that are configured to authenticate the IRS. Response:

* 200 if the IRS exists, returned as JSON: `{ "private_ids": ["<private-id-1>", "<private-id-2>"] }`
* 404 if the IRS does not exist.

    `/irs/<irs-uuid>/private_ids/<private-id>`

Make a PUT to this URL to configure the private ID to authenticate the specified IRS. Response:

* 200 if the private ID has been updated to authenticate the IRS.
* 404 if the IRS or Private ID could not be found.

## Service Profiles

    /irs/<irs-uuid>/service_profiles

Make a POST to this URL to create a new service profile. Response:

* 201, with the URL of the service profile in the Location header: `Location: /irs/<irs-uuid>/service_profiles/<service-profile-uuid>`

    `/irs/<irs-uuid>/service_profiles/<service-profile-uuid>`

Make a DELETE to this URL to delete an existing service profile. Response:

* 200 if the service profile has been deleted.
* 204 if the service profile could not be found.

    `/irs/<irs-uuid>/service_profiles/<service-profile-uuid>/public_ids`

Make a GET to this URL to list the public IDs that use this service profile.  Response:

* 200 if the service profile exists, returned as JSON: `{ "public_ids": ["<public-id-1>", "<public-id-2>"] }`
* 404 if the service profile does not exist.

    `/irs/<irs-uuid>/service_profiles/<service-profile-uuid>/public_ids/<public-id>`

Make a PUT to this URL to create a new public ID, or update an existing one, that uses the specified service profile. The body must be an XML document containing a complete IMS `PublicIdentity` element. Response:

* 200 if the public ID was created / updated successfully.
* 400 if the body of the request is invalid.
* 403 if the identity specified in the URL does not match the identity specified in the PublicIdentity element.
* 404 if the service profile does not exist.

Make a GET to this URL to delete an existing public ID. Response:

* 200 if the public ID was deleted.
* 404 if the public ID does not exist.

    `/irs/<irs-uuid>/service_profiles/<service-profile-uuid>/filter_criteria`

Make a PUT to this URL to set the Initial Filter Criteria for the service profile. The body must be an XML document containing an IMS `ServiceProfile` element, with at least one `InitialFilterCriteria` sub-element. Response:

* 200 if the iFCs were updated successfully.
* 404 if the service profile does not exist.

Make a GET to this URL to retrieve the iFCs for this service profile. Response:

* 200 if the service profile exists and has iFCs configured, returned as an XML document containing an IMS `ServiceProfile` element, with `InitialFilterCriteria` sub-elements.
* 404 if the service profile does not exists, or has no iFCs.

## Public IDs (read only)

    /public/<public-id>/service_profile

Make a GET to this URL to be redirected to the public ID's service profile. Response:

* 303 if the public ID exists, with the service profile URL in the Location header: `Location: /irs/<irs-uuid>/service_profiles/<service-profile-uuid>`
* 404 if the public ID does not exist.

    `/public/<public-id>/irs/`

Make a GET to this URL to be redirected to the public ID's implicit registration set. Response:

* 303 if the public ID exists, with the IRS URL in the Location header: `Location: /irs/<irs-uuid>`
* 404 if the public ID does not exist.

    `/public/<public-id>/associated_private_ids`

Make a GET to this URL to list the private IDs that can authenticate the public ID. Response:

* 200 if the public IDs exists, returned as JSON: `{ "private_ids": ["<private-id-1>", "<private-id-2>"] }`
* 404 if the public ID does not exist.

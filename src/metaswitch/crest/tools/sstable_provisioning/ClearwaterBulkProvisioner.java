/**
 * Based on sample code provided by www.datastax.com, modified to use the homer/homestead
 * column family definitions and data structure.
 *
 * Original source: http://www.datastax.com/dev/blog/bulk-loading
 *                  http://www.datastax.com/wp-content/uploads/2011/08/DataImportExample.java
 */

/**
 * Disclaimer:
 * This file is an example on how to use the Cassandra SSTableSimpleUnsortedWriter class to create
 * sstables from a csv input file.
 * While this has been tested to work, this program is provided "as is" with no guarantee. Moreover,
 * it's primary aim is toward simplicity rather than completness. In partical, don't use this as an
 * example to parse csv files at home.
 */
import java.nio.ByteBuffer;
import java.io.*;
import java.util.UUID;

import org.apache.cassandra.db.marshal.*;
import org.apache.cassandra.io.sstable.SSTableSimpleUnsortedWriter;
import org.apache.cassandra.dht.Murmur3Partitioner;
import static org.apache.cassandra.utils.ByteBufferUtil.bytes;
import static org.apache.cassandra.utils.UUIDGen.decompose;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.w3c.dom.Attr;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.TransformerException;

import java.text.SimpleDateFormat;
import java.text.DateFormat;
import java.util.Date;

import java.util.Random;


/*
 * Utility class to build call list XML documents.
 */
class CallListDocBuilder
{
    public CallListDocBuilder() throws ParserConfigurationException, TransformerException
    {
        docFactory = DocumentBuilderFactory.newInstance();
        docBuilder = docFactory.newDocumentBuilder();

        transformerFactory = TransformerFactory.newInstance();
        transformer = transformerFactory.newTransformer();

        xmlDateTimeFormatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss");

        rng = new Random();
    }

    /*
     * Convert a boolean into its XML representation.
     */
    private String xmlBool(boolean value)
    {
        if (value) {
            return "1";
        } else {
            return "0";
        }
    }

    /*
     * Convert a timestamp (in ms) into the DateTime format used in XML
     * documents.
     */
    private String xmlTimestamp(long timestamp_ms)
    {
        return xmlDateTimeFormatter.format(new Date(timestamp_ms));
    }

    /*
     * Utility method to add a simple XML element containing some text as a
     * child of an existing element.
     *
     * e.g. <simple-element>text</simple-element>
     */
    private void addSimpleTextElement(Document doc,
                                      Element parent,
                                      String tag,
                                      String text)
    {
        Element elem = doc.createElement(tag);
        elem.appendChild(doc.createTextNode(text));
        parent.appendChild(elem);
    }

    /*
     * Add an element containing the identity of the call list owner.
     */
    private Element localIdentityElement(Document doc, String uri, String tag)
    {
        Element topElem = doc.createElement(tag);
        addSimpleTextElement(doc, topElem, "URI", uri);
        // The subscriber's name is often not present in the underlying
        // signaling, so don't include it in the document.
        return topElem;
    }

    /*
     * Add an element containing the name of an identity representing a
     * different subscriber (i.e. not the one that owns the call list).
     */
    private Element remoteIdentityElement(Document doc, String tag)
    {
        // Create a random DN for inclusion in the call list.
        int dn = rng.nextInt(1000000000);

        Element topElem = doc.createElement(tag);
        addSimpleTextElement(doc, topElem, "URI", String.format("sip:%010d@example.com", dn));
        addSimpleTextElement(doc, topElem, "name", String.format("Tel number: %010d", dn));
        return topElem;
    }

    /*
     * Create an entire call list XML document.
     */
    public String createCallListDoc(String uri,
                                    boolean outgoing,
                                    boolean answered,
                                    long timestamp_ms)
        throws TransformerException
    {
        Document doc = docBuilder.newDocument();
        Element callElement = doc.createElement("call");
        doc.appendChild(callElement);

        if (outgoing) {
            callElement.appendChild(localIdentityElement(doc, uri, "from"));
            callElement.appendChild(remoteIdentityElement(doc, "to"));
        } else {
            callElement.appendChild(localIdentityElement(doc, uri, "to"));
            callElement.appendChild(remoteIdentityElement(doc, "from"));
        }

        addSimpleTextElement(doc, callElement, "answered", xmlBool(answered));
        addSimpleTextElement(doc, callElement, "outgoing", xmlBool(outgoing));
        addSimpleTextElement(doc, callElement, "start-time", xmlTimestamp(timestamp_ms));

        if (answered) {
            // The call was answered.  Set the answer time to 10s after the call
            // was started, and the end time to one minute after.
            addSimpleTextElement(doc,
                                 callElement,
                                 "answered-time",
                                 xmlTimestamp(timestamp_ms + (10 * 1000)));
            addSimpleTextElement(doc,
                                 callElement,
                                 "end-time",
                                 xmlTimestamp(timestamp_ms + (60 * 1000)));
        }

        // Convert the document to a string and return it.
        Writer out = new StringWriter();
        transformer.transform(new DOMSource(doc), new StreamResult(out));
        return out.toString();
    }

    DocumentBuilderFactory docFactory;
    DocumentBuilder docBuilder;

    TransformerFactory transformerFactory;
    Transformer transformer;

    DateFormat xmlDateTimeFormatter;

    Random rng;
}

public class ClearwaterBulkProvisioner
{
    public static void main(String[] args) throws IOException
    {
        if (args.length != 2)
        {
            System.out.println("Usage:\n  BulkProvision <csv_file> <role>");
            System.exit(1);
        }

        String csvfile = args[0];
        String role = args[1];

        if (role.equals("homer")) {
            provision_homer(csvfile);
        } else if (role.equals("homestead-local")) {
            // Provision Homestead with cache and provisioning tables
            provision_homestead_cache(csvfile);
            provision_homestead_provisioning(csvfile);
        } else if (role.equals("homestead-hss")) {
            // Provision Homestead with cache tables only
            provision_homestead_cache(csvfile);
        } else if (role.equals("memento")) {
            try {
                // Provision test memento data.
                provision_memento(csvfile);
            }
            catch(ParserConfigurationException ex) {
                ex.printStackTrace();
            }
            catch (TransformerException ex) {
                ex.printStackTrace();
            }
        } else {
           System.out.println("Only homer, homestead-local, homestead-hss and memento roles are supported");
        }
    }

    private static void provision_homer(String csvfile) throws IOException
    {
        BufferedReader reader = new BufferedReader(new FileReader(csvfile));

        String keyspace = "homer";
        File ks_directory = new File(keyspace);
        if (!ks_directory.exists())
            ks_directory.mkdir();

        SSTableSimpleUnsortedWriter simservsWriter = createWriter(keyspace, "simservs");

        String line;
        int lineNumber = 1;
        CsvEntry entry = new CsvEntry();
        // There is no reason not to use the same timestamp for every column in that example.
        long timestamp = System.currentTimeMillis() * 1000;
        while ((line = reader.readLine()) != null)
        {
            if (entry.parse(line, lineNumber, csvfile))
            {
                simservsWriter.newRow(bytes(entry.public_id));
                simservsWriter.addColumn(bytes("value"), bytes(entry.simservs), timestamp);
            }
            lineNumber++;
        }
        // Don't forget to close!
        simservsWriter.close();
    }

    private static void provision_homestead_cache(String csvfile) throws IOException
    {
        BufferedReader reader = new BufferedReader(new FileReader(csvfile));

        /*
         * Create the directory to hold the cache keyspace.
         */
        String cache_keyspace = "homestead_cache";
        File cache_ks_directory = new File(cache_keyspace);
        if (!cache_ks_directory.exists())
            cache_ks_directory.mkdir();

        /*
         * Create SSTable writers for each table in the cache keyspace.
         */
        SSTableSimpleUnsortedWriter impiWriter = createWriter(cache_keyspace, "impi");
        SSTableSimpleUnsortedWriter impuWriter = createWriter(cache_keyspace, "impu");

        // There is no reason not to use the same timestamp for every column.
        long timestamp = System.currentTimeMillis() * 1000;

        /*
         * Walk through the supplied CSV, inserting rows in the keyspaces for each entry.
         */
        String line;
        int lineNumber = 1;
        CsvEntry entry = new CsvEntry();

        while ((line = reader.readLine()) != null)
        {
            if (entry.parse(line, lineNumber, csvfile))
            {
                impiWriter.newRow(bytes(entry.private_id));
                impiWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                impiWriter.addColumn(bytes("digest_ha1"), bytes(entry.digest), timestamp);
                impiWriter.addColumn(bytes("digest_realm"), bytes(entry.realm), timestamp);
                impiWriter.addColumn(bytes("public_id_" + entry.public_id), bytes(entry.public_id), timestamp);

                impuWriter.newRow(bytes(entry.public_id));
                impuWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                impuWriter.addColumn(bytes("ims_subscription_xml"), bytes(entry.imssubscription), timestamp);
            }
            lineNumber++;
        }

        // Don't forget to close!
        impiWriter.close();
        impuWriter.close();
    }

    private static void provision_homestead_provisioning(String csvfile) throws IOException
    {
        BufferedReader reader = new BufferedReader(new FileReader(csvfile));

        /*
         * Create the directory to hold the provisioning keyspace.
         */
        String prov_keyspace = "homestead_provisioning";
        File prov_ks_directory = new File(prov_keyspace);
        if (!prov_ks_directory.exists())
            prov_ks_directory.mkdir();

        /*
         * Create SSTable writers for each table in the provisioning keyspace.
         */
        SSTableSimpleUnsortedWriter irsWriter = createWriter(prov_keyspace, "implicit_registration_sets", UUIDType.instance);
        SSTableSimpleUnsortedWriter spWriter = createWriter(prov_keyspace, "service_profiles", UUIDType.instance);
        SSTableSimpleUnsortedWriter publicWriter = createWriter(prov_keyspace, "public");
        SSTableSimpleUnsortedWriter privateWriter = createWriter(prov_keyspace, "private");

        /*
         * Walk through the supplied CSV, inserting rows in the keyspaces for each entry.
         */
        String line;
        int lineNumber = 1;
        CsvEntry entry = new CsvEntry();

        // There is no reason not to use the same timestamp for every column.
        long timestamp = System.currentTimeMillis() * 1000;

        while ((line = reader.readLine()) != null)
        {
            if (entry.parse(line, lineNumber, csvfile))
            {
                irsWriter.newRow(entry.irs_uuid);
                irsWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                irsWriter.addColumn(bytes("associated_private_" + entry.private_id), bytes(entry.private_id), timestamp);
                irsWriter.addColumn(bytes("service_profile_" + entry.sp_uuid_str), entry.sp_uuid, timestamp);

                spWriter.newRow(entry.sp_uuid);
                spWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                spWriter.addColumn(bytes("public_identity_" + entry.public_id), bytes(entry.public_id), timestamp);
                spWriter.addColumn(bytes("initialfiltercriteria"), bytes(entry.ifc), timestamp);
                spWriter.addColumn(bytes("irs"), entry.irs_uuid, timestamp);

                publicWriter.newRow(bytes(entry.public_id));
                publicWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                publicWriter.addColumn(bytes("publicidentity"), bytes(entry.publicidentity_xml), timestamp);
                publicWriter.addColumn(bytes("service_profile"), entry.sp_uuid, timestamp);

                privateWriter.newRow(bytes(entry.private_id));
                privateWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
                privateWriter.addColumn(bytes("digest_ha1"), bytes(entry.digest), timestamp);
                privateWriter.addColumn(bytes("realm"), bytes(entry.realm), timestamp);
                privateWriter.addColumn(bytes("associated_irs_" + entry.irs_uuid_str), entry.irs_uuid, timestamp);
            }
            lineNumber++;
        }

        // Don't forget to close!
        irsWriter.close();
        spWriter.close();
        publicWriter.close();
        privateWriter.close();
    }

    private static void provision_memento(String csvfile)
        throws IOException, ParserConfigurationException, TransformerException
    {
        // The number of call list entries to write.
        final int CALL_LIST_NUM_CALLS = 150;

        // The period over which to write call list entries (1 week).
        final long CALL_LIST_TIME_RANGE_MS = 7 * 24 * 60 * 60 * 1000;

        // Create an object to create call list XML documents.
        CallListDocBuilder callListBuilder = new CallListDocBuilder();

        // Puts a date into the correct format for use in a memento colunn
        // name.
        DateFormat df = new SimpleDateFormat("yyyyMMddHHmmss");

        // Used to randomize call list entries.
        Random rng = new Random();

        /*
         * Create the directory to hold the memento keyspace.
         */
        String keyspace = "memento";
        File ks_directory = new File(keyspace);
        if (!ks_directory.exists()) {
            ks_directory.mkdir();
        }

        /*
         * Create SSTable writers for the call_lists table.
         */
        SSTableSimpleUnsortedWriter callListWriter = createWriter(keyspace, "call_lists");
        BufferedReader reader = new BufferedReader(new FileReader(csvfile));

        /*
         * Walk through the supplied CSV, inserting rows in the keyspaces for each entry.
         */
        String line;
        int lineNumber = 1;
        CsvEntry entry = new CsvEntry();

        // There is no reason not to use the same cassandra timestamp for every
        // column.
        long timestamp_ms = System.currentTimeMillis();
        long timestamp_us = timestamp_ms * 1000;

        while ((line = reader.readLine()) != null)
        {
            if (entry.parse(line, lineNumber, csvfile))
            {
                callListWriter.newRow(bytes(entry.public_id));

                for (int ii = 0; ii < CALL_LIST_NUM_CALLS; ii++)
                {
                    // Work out what time the call started. We spread calls
                    // evenly over the time range.
                    long list_timestamp_ms = timestamp_ms -
                                             CALL_LIST_TIME_RANGE_MS +
                                             (ii * CALL_LIST_TIME_RANGE_MS / CALL_LIST_NUM_CALLS);
                    // Randomize the timestamp by 1hr to defeat compression.
                    list_timestamp_ms += rng.nextInt(60 * 60 * 1000);

                    String column_prefix = String.format("call_%s_%016x_",
                                                         df.format(new Date(list_timestamp_ms)),
                                                         ii);

                    // Create a call list document.  Randomly decide if it was
                    // answered, and incoming/outgoing.
                    boolean answered = (rng.nextFloat() < 0.8);
                    boolean outgoing = (rng.nextFloat() < 0.5);

                    String xml = callListBuilder.createCallListDoc(entry.public_id,
                                                                   outgoing,
                                                                   answered,
                                                                   list_timestamp_ms);
                    if (answered)
                    {
                        // For an answered call strip off the outer
                        // <call></call> tags then split the record in two:
                        // -  The begin fragment contains everything up to (but
                        //    not including) the <end-time>.
                        // -  The end fragment is everything else.
                        String begin_fragment;
                        String end_fragment;
                        begin_fragment = xml.substring(xml.indexOf("<call>") + "<call>".length(),
                                                       xml.indexOf("<end-time>"));
                        end_fragment = xml.substring(xml.indexOf("<end-time>"),
                                                     xml.indexOf("</call>"));

                        callListWriter.addColumn(bytes(column_prefix + "begin"),
                                                 bytes(begin_fragment),
                                                 timestamp_us);
                        callListWriter.addColumn(bytes(column_prefix + "end"),
                                                 bytes(end_fragment),
                                                 timestamp_us);
                    }
                    else
                    {
                        // For a rejected call just strip off the <call></call>
                        // tags and write a column.
                        String fragment = xml.substring(xml.indexOf("<call>") + "<call>".length(),
                                                        xml.indexOf("</call>"));
                        callListWriter.addColumn(bytes(column_prefix + "rejected"),
                                                 bytes(fragment),
                                                 timestamp_us);
                    }
                }
            }
            lineNumber++;
        }

        // Don't forget to close!
        callListWriter.close();
    }

    private static SSTableSimpleUnsortedWriter createWriter(String keyspace_name, String table_name) throws IOException
    {
        return createWriter(keyspace_name, table_name, AsciiType.instance);
    }

    private static SSTableSimpleUnsortedWriter createWriter(String keyspace_name, String table_name, AbstractType comparator) throws IOException
    {
        File directory = new File(keyspace_name + "/" + table_name);
        if (!directory.exists())
            directory.mkdir();

        return new SSTableSimpleUnsortedWriter(directory,
                                               new Murmur3Partitioner(),
                                               keyspace_name,
                                               table_name,
                                               comparator,
                                               null,
                                               64);
    }

    static class CsvEntry
    {
      String public_id, private_id, realm, digest, simservs, ifc, imssubscription, publicidentity_xml, irs_uuid_str, sp_uuid_str;
      ByteBuffer irs_uuid, sp_uuid;

        boolean parse(String line, int lineNumber, String csvfile)
        {
            // Ghetto csv parsing, will break if any entries contain commas.  This is fine at the moment because
            // neither the default simservs, nor the default IFC contain commas.
            String[] columns = line.split(",");
            if (columns.length != 10)
            {
                System.out.println(String.format("Invalid input '%s' at line %d of %s", line, lineNumber, csvfile));
                return false;
            }
            public_id = columns[0].trim();
            private_id = columns[1].trim();
            realm = columns[2].trim();
            digest = columns[3].trim();
            simservs = columns[4].trim();
            publicidentity_xml = columns[5].trim();
            ifc = columns[6].trim();
            imssubscription = columns[7].trim();
            irs_uuid_str = columns[8].trim();
            sp_uuid_str = columns[9].trim();

            // Convert the string representation of UUID to a byte array.  Apache Commons' UUID class has this
            // as built in function (as getRawBytes) but we don't have access to that class here, so we roll our
            // own.
            UUID uuid = UUID.fromString(irs_uuid_str);
            irs_uuid = ByteBuffer.wrap(decompose(uuid));
            UUID uuid2 = UUID.fromString(sp_uuid_str);
            sp_uuid = ByteBuffer.wrap(decompose(uuid2));

            return true;
        }
    }
}

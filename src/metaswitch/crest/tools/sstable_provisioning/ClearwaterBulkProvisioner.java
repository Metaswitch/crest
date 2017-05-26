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
import java.util.Iterator;
import java.util.Random;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.Charset;


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

// A subscriber to be provisioned.
class Subscriber
{
    String public_id, private_id, realm, digest, simservs, ifc, imssubscription, publicidentity_xml, irs_uuid_str, sp_uuid_str, password_to_write;
    ByteBuffer irs_uuid, sp_uuid;
}

// A subscriber parsed from a CSV file.
class CsvSubscriber extends Subscriber
{
    boolean parse(String line, int lineNumber, String csvfile, boolean writePlaintextPassword)
    {
        // Ghetto csv parsing, will break if any entries contain commas.  This is fine at the moment because
        // neither the default simservs, nor the default IFC contain commas.
        String[] columns = line.split(",");

        if (columns.length != 11)
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
        password_to_write = writePlaintextPassword ? columns[10].trim() : "";

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

// Basic subscriber iterator implementation - extended by Csv... and Range... classes.
abstract class BaseSubscriberIterator implements Iterator<Subscriber>
{
    private Subscriber mSubscriber = null;

    public boolean hasNext()
    {
        return (getSubscriber() != null);
    }

    public Subscriber next()
    {
        Subscriber sub = getSubscriber();
        mSubscriber = null;
        return sub;
    }

    public void remove()
    {
        throw new UnsupportedOperationException();
    }

    private Subscriber getSubscriber()
    {
        if (mSubscriber == null)
        {
            mSubscriber = getNextSubscriber();
        }
        return mSubscriber;
    }

    // Get the next subscriber.
    protected abstract Subscriber getNextSubscriber();
}

// Iterates through subscribers read from a CSV file.
class CsvSubscriberIterator extends BaseSubscriberIterator
{
    private String mCsvfile;
    private BufferedReader mReader;
    private boolean mWritePlaintextPassword;
    private int mLineNumber = 1;

    CsvSubscriberIterator(String csvfile, boolean writePlaintextPassword) throws IOException
    {
        mCsvfile = csvfile;
        mReader = new BufferedReader(new FileReader(csvfile));
        mWritePlaintextPassword = writePlaintextPassword;
    }

    protected Subscriber getNextSubscriber()
    {
        CsvSubscriber sub = new CsvSubscriber();
        try
        {
            String line;

            if (((line = mReader.readLine()) == null) ||
                (!sub.parse(line, mLineNumber, mCsvfile, mWritePlaintextPassword)))
            {
                sub = null;
            }

            mLineNumber++;
        }
        catch (IOException e)
        {
            System.err.println("Caught " + e + " while reading " + mCsvfile);
            e.printStackTrace(System.err);
            sub = null;
        }
        return sub;
    }
}

// Iterates through subscribers in a range.
class RangeSubscriberIterator extends BaseSubscriberIterator
{
    // These are very basic, but sufficient for testing.
    static final String XML_DECLARATION = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    static final String EMPTY_SIMSERVS_XML = "<simservs xmlns=\"http://uri.etsi.org/ngn/params/xml/simservs/xcap\" />";
    static final String SERVICE_PROFILE_XML_PREFIX = "<ServiceProfile>";
    static final String EMPTY_IFC_XML =                "<InitialFilterCriteria/>";
    static final String SERVICE_PROFILE_XML_SUFFIX = "</ServiceProfile>";
    static final String PUBLIC_IDENTITY_XML_PREFIX = "<PublicIdentity>" +
                                                       "<Identity>";
    static final String PUBLIC_IDENTITY_XML_SUFFIX =   "</Identity>" +
                                                     "</PublicIdentity>";
    static final String IMS_SUBSCRIPTION_XML_PREFIX = "<IMSSubscription xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"CxDataType.xsd\">" +
                                                         "<PrivateID>Unspecified</PrivateID>";
    static final String IMS_SUBSCRIPTION_XML_SUFFIX = "</IMSSubscription>";

    long mNumber;
    long mEndNumber;
    String mDomain;
    String mPassword;
    MessageDigest mDigest;
    boolean mWritePlaintextPassword;

    // Somewhat limited set of parameters at the moment.  We might extend this in future, but
    // it's sufficient for stress testing (which is what this is aimed at).
    RangeSubscriberIterator(long startNumber, long endNumber, String domain, String password, boolean writePlaintextPassword) throws NoSuchAlgorithmException
    {
        mNumber = startNumber;
        mEndNumber = endNumber;
        mDomain = domain;
        mPassword = password;
        mDigest = MessageDigest.getInstance("MD5");
        mWritePlaintextPassword = writePlaintextPassword;
    }

    protected Subscriber getNextSubscriber()
    {
        Subscriber sub = null;
        if (mNumber <= mEndNumber)
        {
            sub = new Subscriber();
            sub.public_id = "sip:" + mNumber + "@" + mDomain;
            sub.private_id = mNumber + "@" + mDomain;
            sub.realm = mDomain;
            sub.password_to_write = mWritePlaintextPassword ? mPassword : "";
            sub.digest = ha1(sub.private_id);
            sub.simservs = XML_DECLARATION + EMPTY_SIMSERVS_XML;
            sub.publicidentity_xml = PUBLIC_IDENTITY_XML_PREFIX + sub.public_id + PUBLIC_IDENTITY_XML_SUFFIX;
            sub.ifc = XML_DECLARATION + SERVICE_PROFILE_XML_PREFIX + EMPTY_IFC_XML + SERVICE_PROFILE_XML_SUFFIX;
            sub.imssubscription = XML_DECLARATION + IMS_SUBSCRIPTION_XML_PREFIX + SERVICE_PROFILE_XML_PREFIX + sub.publicidentity_xml + SERVICE_PROFILE_XML_SUFFIX + IMS_SUBSCRIPTION_XML_SUFFIX;
            sub.irs_uuid = ByteBuffer.wrap(decompose(UUID.randomUUID()));
            sub.sp_uuid = ByteBuffer.wrap(decompose(UUID.randomUUID()));
            mNumber++;
        }
        return sub;
    }

    private String ha1(String private_id)
    {
        String plain = private_id + ":" + mDomain + ":" + mPassword;
        byte[] digest = mDigest.digest(plain.getBytes(Charset.forName("UTF-8")));
        mDigest.reset();
        return toHex(digest);
    }

    private String toHex(byte[] bytes)
    {
        StringBuffer sb = new StringBuffer();
        for (int i = 0; i < bytes.length; ++i)
        {
            sb.append(Integer.toHexString((bytes[i] & 0xff) | 0x100).substring(1,3));
        }
        return sb.toString();
    }
}

public class ClearwaterBulkProvisioner
{
    public static void main(String[] args) throws IOException, NoSuchAlgorithmException
    {
        String role = null;
        Iterator<Subscriber> subs = null;
        Iterator<Subscriber> subs2 = null;

        // Decide how we've been called based on the number of args. This is fairly hacky
        // and will break as soon as we add another optional parameter, but it's good
        // enough for now.
        // If there are 2/3 args, we're pulling values from a CSV file. 5/6 args and we're
        // taking values from the command line.
        if (args.length == 2)
        {
            role = args[0];
            subs = new CsvSubscriberIterator(args[1], false);
            subs2 = new CsvSubscriberIterator(args[1], false);
        }
        else if (args.length == 3)
        {
            role = args[0];
            subs = new CsvSubscriberIterator(args[1], true);
            subs2 = new CsvSubscriberIterator(args[1], true);
        }
        else if (args.length == 5)
        {
            role = args[0];
            subs = new RangeSubscriberIterator(Long.parseLong(args[1]), Long.parseLong(args[2]), args[3], args[4], false);
            subs2 = new RangeSubscriberIterator(Long.parseLong(args[1]), Long.parseLong(args[2]), args[3], args[4], false);
        }
        else if (args.length == 6)
        {
            role = args[0];
            subs = new RangeSubscriberIterator(Long.parseLong(args[1]), Long.parseLong(args[2]), args[3], args[4], true);
            subs2 = new RangeSubscriberIterator(Long.parseLong(args[1]), Long.parseLong(args[2]), args[3], args[4], true);
        }
        else
        {
            System.out.println("Usage:\n  BulkProvision <role> (<csv_file>|<start_dn> <end_dn> <domain> <password>) [<plaintext_password>]");
            System.exit(1);
        }

        if (role.equals("homer"))
        {
            provision_homer(subs);
        }
        else if (role.equals("homestead-local"))
        {
            // Provision Homestead with cache and provisioning tables
            provision_homestead_cache(subs);
            provision_homestead_provisioning(subs2);
        }
        else if (role.equals("homestead-hss"))
        {
            // Provision Homestead with cache tables only
            provision_homestead_cache(subs);
        }
        else if (role.equals("memento"))
        {
            try
            {
                // Provision test memento data.
                provision_memento(subs);
            }
            catch(ParserConfigurationException ex)
            {
                ex.printStackTrace();
            }
            catch (TransformerException ex)
            {
                ex.printStackTrace();
            }
        }
        else
        {
           System.out.println("Only homer, homestead-local, homestead-hss and memento roles are supported");
        }
    }

    private static void provision_homer(Iterator<Subscriber> subs) throws IOException
    {
        String keyspace = "homer";
        File ks_directory = new File(keyspace);
        if (!ks_directory.exists())
            ks_directory.mkdir();

        SSTableSimpleUnsortedWriter simservsWriter = createWriter(keyspace, "simservs");

        // There is no reason not to use the same timestamp for every column in that example.
        long timestamp = System.currentTimeMillis() * 1000;

        /*
         * Walk through the supplied subscribers, inserting rows in the keyspaces for each entry.
         */
        while (subs.hasNext())
        {
            Subscriber sub = subs.next();
            simservsWriter.newRow(bytes(sub.public_id));
            simservsWriter.addColumn(bytes("value"), bytes(sub.simservs), timestamp);
        }

        // Don't forget to close!
        simservsWriter.close();
    }

    private static void provision_homestead_cache(Iterator<Subscriber> subs) throws IOException
    {
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
         * Walk through the supplied subscribers, inserting rows in the keyspaces for each entry.
         */
        while (subs.hasNext())
        {
            Subscriber sub = subs.next();
            impiWriter.newRow(bytes(sub.private_id));
            impiWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            impiWriter.addColumn(bytes("digest_ha1"), bytes(sub.digest), timestamp);
            impiWriter.addColumn(bytes("digest_realm"), bytes(sub.realm), timestamp);
            impiWriter.addColumn(bytes("public_id_" + sub.public_id), bytes(sub.public_id), timestamp);

            impuWriter.newRow(bytes(sub.public_id));
            impuWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            impuWriter.addColumn(bytes("ims_subscription_xml"), bytes(sub.imssubscription), timestamp);
        }

        // Don't forget to close!
        impiWriter.close();
        impuWriter.close();
    }

    private static void provision_homestead_provisioning(Iterator<Subscriber> subs) throws IOException
    {
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

        // There is no reason not to use the same timestamp for every column.
        long timestamp = System.currentTimeMillis() * 1000;

        /*
         * Walk through the supplied subscribers, inserting rows in the keyspaces for each entry.
         */
        while (subs.hasNext())
        {
            Subscriber sub = subs.next();
            irsWriter.newRow(sub.irs_uuid);
            irsWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            irsWriter.addColumn(bytes("associated_private_" + sub.private_id), bytes(sub.private_id), timestamp);
            irsWriter.addColumn(bytes("service_profile_" + sub.sp_uuid_str), sub.sp_uuid, timestamp);

            spWriter.newRow(sub.sp_uuid);
            spWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            spWriter.addColumn(bytes("public_identity_" + sub.public_id), bytes(sub.public_id), timestamp);
            spWriter.addColumn(bytes("initialfiltercriteria"), bytes(sub.ifc), timestamp);
            spWriter.addColumn(bytes("irs"), sub.irs_uuid, timestamp);

            publicWriter.newRow(bytes(sub.public_id));
            publicWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            publicWriter.addColumn(bytes("publicidentity"), bytes(sub.publicidentity_xml), timestamp);
            publicWriter.addColumn(bytes("service_profile"), sub.sp_uuid, timestamp);

            privateWriter.newRow(bytes(sub.private_id));
            privateWriter.addColumn(bytes("_exists"), bytes(""), timestamp);
            privateWriter.addColumn(bytes("digest_ha1"), bytes(sub.digest), timestamp);
            privateWriter.addColumn(bytes("plaintext_password"), bytes(sub.password_to_write), timestamp);
            privateWriter.addColumn(bytes("realm"), bytes(sub.realm), timestamp);
            privateWriter.addColumn(bytes("associated_irs_" + sub.irs_uuid_str), sub.irs_uuid, timestamp);
        }

        // Don't forget to close!
        irsWriter.close();
        spWriter.close();
        publicWriter.close();
        privateWriter.close();
    }

    private static void provision_memento(Iterator<Subscriber> subs)
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

        // There is no reason not to use the same cassandra timestamp for every
        // column.
        long timestamp_ms = System.currentTimeMillis();
        long timestamp_us = timestamp_ms * 1000;

        /*
         * Walk through the supplied subscribers, inserting rows in the keyspaces for each entry.
         */
        while (subs.hasNext())
        {
            Subscriber sub = subs.next();
            callListWriter.newRow(bytes(sub.public_id));

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

                String xml = callListBuilder.createCallListDoc(sub.public_id,
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
}

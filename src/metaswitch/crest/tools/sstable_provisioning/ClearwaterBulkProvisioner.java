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
import org.apache.cassandra.dht.RandomPartitioner;
import static org.apache.cassandra.utils.ByteBufferUtil.bytes;
import static org.apache.cassandra.utils.UUIDGen.decompose;

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

        BufferedReader reader = new BufferedReader(new FileReader(csvfile));

        if (role.equals("homer")) {
            provision_homer(reader, csvfile);
        } else if (role.equals("homestead")) {
            provision_homestead(reader, csvfile);
        } else {
           System.out.println("Only homer and homestead roles are supported");
        }
    }

    private static void provision_homer(BufferedReader reader, String csvfile) throws IOException
    {
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

    private static void provision_homestead(BufferedReader reader, String csvfile) throws IOException
    {
        /*
         * Create the directories to hold the two keyspaces.
         */
        String cache_keyspace = "homestead_cache";
        File cache_ks_directory = new File(cache_keyspace);
        if (!cache_ks_directory.exists())
            cache_ks_directory.mkdir();

        String prov_keyspace = "homestead_provisioning";
        File prov_ks_directory = new File(prov_keyspace);
        if (!prov_ks_directory.exists())
            prov_ks_directory.mkdir();

        /*
         * Create SSTable writes for each table in the keyspaces.
         */
        SSTableSimpleUnsortedWriter impiWriter = createWriter(cache_keyspace, "impi");
        SSTableSimpleUnsortedWriter impuWriter = createWriter(cache_keyspace, "impu");
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
                impiWriter.newRow(bytes(entry.private_id));
                impiWriter.addColumn(bytes("digest_ha1"), bytes(entry.digest), timestamp);
                impiWriter.addColumn(bytes("public_id_" + entry.public_id), bytes(entry.public_id), timestamp);

                impuWriter.newRow(bytes(entry.public_id));
                impuWriter.addColumn(bytes("ims_subscription_xml"), bytes(entry.imssubscription), timestamp);

                irsWriter.newRow(entry.irs_uuid);
                irsWriter.addColumn(bytes("associated_private_" + entry.private_id), bytes(entry.private_id), timestamp);
                irsWriter.addColumn(bytes("service_profile_" + entry.sp_uuid_str), entry.sp_uuid, timestamp);

                spWriter.newRow(entry.sp_uuid);
                spWriter.addColumn(bytes("public_identity_" + entry.public_id), bytes(entry.public_id), timestamp);
                spWriter.addColumn(bytes("initialfiltercriteria"), bytes(entry.ifc), timestamp);
                spWriter.addColumn(bytes("irs"), entry.irs_uuid, timestamp);

                publicWriter.newRow(bytes(entry.public_id));
                publicWriter.addColumn(bytes("publicidentity"), bytes(entry.publicidentity_xml), timestamp);
                publicWriter.addColumn(bytes("service_profile"), entry.sp_uuid, timestamp);

                privateWriter.newRow(bytes(entry.private_id));
                privateWriter.addColumn(bytes("digest_ha1"), bytes(entry.digest), timestamp);
                privateWriter.addColumn(bytes("associated_irs_" + entry.irs_uuid_str), entry.irs_uuid, timestamp);
            }
            lineNumber++;
        }

        // Don't forget to close!
        impiWriter.close();
        impuWriter.close();
        irsWriter.close();
        spWriter.close();
        publicWriter.close();
        privateWriter.close();
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
                                               new RandomPartitioner(),
                                               keyspace_name,
                                               table_name,
                                               comparator,
                                               null,
                                               32);
    }

    static class CsvEntry
    {
      String public_id, private_id, digest, simservs, ifc, imssubscription, publicidentity_xml, irs_uuid_str, sp_uuid_str;
      ByteBuffer irs_uuid, sp_uuid;

        boolean parse(String line, int lineNumber, String csvfile)
        {
            // Ghetto csv parsing, will break if any entries contain commas.  This is fine at the moment because
            // neither the default simservs, nor the default IFC contain commas.
            String[] columns = line.split(",");
            if (columns.length != 9)
            {
                System.out.println(String.format("Invalid input '%s' at line %d of %s", line, lineNumber, csvfile));
                return false;
            }
            public_id = columns[0].trim();
            private_id = columns[1].trim();
            digest = columns[2].trim();
            simservs = columns[3].trim();
            publicidentity_xml = columns[4].trim();
            ifc = columns[5].trim();
            imssubscription = columns[6].trim();
            irs_uuid_str = columns[7].trim();
            sp_uuid_str = columns[8].trim();

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

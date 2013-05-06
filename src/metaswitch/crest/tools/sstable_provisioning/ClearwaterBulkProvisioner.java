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

        String table = "simservs";
        File directory = new File(keyspace + "/" + table);
        if (!directory.exists())
            directory.mkdir();

        SSTableSimpleUnsortedWriter simservsWriter = new SSTableSimpleUnsortedWriter(
                directory,
                new RandomPartitioner(),
                keyspace,
                "simservs",
                AsciiType.instance,
                null,
                64);

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
        System.exit(0);
    }

    private static void provision_homestead(BufferedReader reader, String csvfile) throws IOException
    {
        String keyspace = "homestead";
        File ks_directory = new File(keyspace);
        if (!ks_directory.exists())
            ks_directory.mkdir();

        String digest_table = "sip_digests";
        File digest_directory = new File(keyspace + "/" + digest_table);
        if (!digest_directory.exists())
            digest_directory.mkdir();

        SSTableSimpleUnsortedWriter digestWriter = new SSTableSimpleUnsortedWriter(
                digest_directory,
                new RandomPartitioner(),
                keyspace,
                digest_table,
                AsciiType.instance,
                null,
                64);

        String ifc_table = "filter_criteria";
        File ifc_directory = new File(keyspace + "/" + ifc_table);
        if (!ifc_directory.exists())
            ifc_directory.mkdir();

        SSTableSimpleUnsortedWriter ifcWriter = new SSTableSimpleUnsortedWriter(
                ifc_directory,
                new RandomPartitioner(),
                keyspace,
                ifc_table,
                AsciiType.instance,
                null,
                64);

        String line;
        int lineNumber = 1;
        CsvEntry entry = new CsvEntry();
        // There is no reason not to use the same timestamp for every column in that example.
        long timestamp = System.currentTimeMillis() * 1000;
        while ((line = reader.readLine()) != null)
        {
            if (entry.parse(line, lineNumber, csvfile))
            {
                digestWriter.newRow(bytes(entry.private_id));
                digestWriter.addColumn(bytes("digest"), bytes(entry.digest), timestamp);
                ifcWriter.newRow(bytes(entry.public_id));
                ifcWriter.addColumn(bytes("value"), bytes(entry.ifc), timestamp);
            }
            lineNumber++;
        }
        // Don't forget to close!
        digestWriter.close();
        ifcWriter.close();
        System.exit(0);
    }

    static class CsvEntry
    {
        String public_id, private_id, digest, simservs, ifc;

        boolean parse(String line, int lineNumber, String csvfile)
        {
            // Ghetto csv parsing, will break if any entries contain commas.  This is fine at the moment because
            // neither the default simservs, nor the default IFC contain commas.
            String[] columns = line.split(",");
            if (columns.length != 5)
            {
                System.out.println(String.format("Invalid input '%s' at line %d of %s", line, lineNumber, csvfile));
                return false;
            }
            try
            {
                public_id = columns[0].trim();
                private_id = columns[1].trim();
                digest = columns[2].trim();
                simservs = columns[3].trim();
                ifc = columns[4].trim();
                return true;
            }
        }
    }
}

all : ClearwaterBulkProvisioner.class

clean :
	-rm -f *.class

ClearwaterBulkProvisioner.class : ClearwaterBulkProvisioner.java
	javac -cp /usr/share/cassandra/apache-cassandra.jar ClearwaterBulkProvisioner.java

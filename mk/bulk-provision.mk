# Included mk file for the bulk provisioner

BULK_PROV_DIR := src/metaswitch/crest/tools/sstable_provisioning

bulk-prov: 
	${MAKE} -C ${BULK_PROV_DIR}

bulk-prov_test:
	@echo "No tests for bulk-prov"

bulk-prov_clean:
	${MAKE} -C ${BULK_PROV_DIR} clean

bulk-prov_distclean:
	${MAKE} -C ${BULK_PROV_DIR} clean

.PHONY: bulk-prov bulk-prov_test bulk-prov_clean bulk-prov_distclean

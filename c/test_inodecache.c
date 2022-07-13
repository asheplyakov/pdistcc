#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "inodecache.h"

int get_gcc_triplet(const char *compiler, char **tripletptr) {
	int err = 0;
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0;
	ssize_t len = -1;
	char *newlineptr = NULL;

	if (!tripletptr) {
		err = -EINVAL;
		goto out;
	}

	if (asprintf(&cmd, "%s -dumpmachine", compiler) < 0) {
		cmd = NULL;
		err = -ENOMEM;
		goto out;
	}

	gccpipe = popen(cmd, "r");
	if (!gccpipe) {
		err = errno ? -errno : -ENOMEM;
		printf("%s: popen failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if ((len = getline(tripletptr, &bufsz, gccpipe)) < 0) {
		err = -errno;
		free(*tripletptr);
		goto out;
	}

	newlineptr = strchr(*tripletptr, '\n');
	if (newlineptr) {
		*newlineptr = '\0';
	}
out:
	if (gccpipe) {
		pclose(gccpipe);
	}
	free(cmd);
	return err;
}

int main(int argc, char **argv) {
	int err = 0;
	uint16_t entry_type = 1;
	char *value = NULL;
	const char* test_value = NULL;
	const char* compiler = NULL;
	struct inode_cache ic = { .dir = "/home/asheplyakov/.cache/pdistcc/icache", .dirfd = -1 };
	char *triplet = NULL;

	if (argc != 3) {
		printf("usage: test_inodecache /path/to/binary value\n");
		return 2;
	}
	compiler = argv[1];
	test_value = argv[2];

	if ((err = inode_cache_open(&ic)) != 0) {
		printf("*** Failed to open inode cache, error %d (%s)\n", err, strerror(-err));
		goto out;
	}
	if ((err = inode_cache_del(&ic, compiler, entry_type)) != 0) {
		printf("*** Failed to purge %s from cache: %d (%s)\n", compiler, err, strerror(err));
		goto out;
	}
	if ((err = inode_cache_put(&ic, compiler, entry_type, test_value)) != 0) {
		printf("*** Failed to put %s => %s to cache: %d (%s)\n",
			compiler, test_value, err, strerror(err));
		goto out;
	}
	if ((err = inode_cache_get(&ic, compiler, entry_type, &value)) != 0) {
		printf("*** Failed to retrive value from cache: %d (%s)\n", err, strerror(-err));
		goto out;
	}
	printf("inode_cache(%s) = %s\n", compiler, value);
	if (strcmp(value, test_value) != 0) {
		printf("*** Wrong value from inode cache for %s: expected %s, actual %s\n",
			compiler, test_value, value);
		err = 7;
		goto out;
	}

	free(value);
	value = NULL;

	if ((err = get_gcc_triplet(compiler, &triplet)) != 0) {
		printf("*** Failed to figure out GCC triplet: %d (%s)\n", err, strerror(-err));
		goto out;
	}
	printf("triplet of %s: %s\n", compiler, triplet);

	if ((err = inode_cache_put(&ic, compiler, entry_type, triplet)) != 0) {
		printf("*** Failed to put %s => %s to cache: %d (%s)\n",
			compiler, triplet, err, strerror(err));
		goto out;
	}


	if ((err = inode_cache_get(&ic, compiler, entry_type, &value)) != 0) {
		printf("*** Failed to get value from cache for %s: %d (%s)\n",
			compiler, err, strerror(-err));
		goto out;
	}

	if (strcmp(value, triplet) != 0) {
		printf("*** Wrong value from inode cache for %s: expected %s, actual %s\n",
			compiler, test_value, value);
		err = 11;
		goto out;
	}

	printf("triplet of %s from inode cache: %s\n", compiler, value);

out:
	free(value);
	inode_cache_close(&ic);
	return err < 0 ? -err : err;
}


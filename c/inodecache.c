#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include "md5.h"
#include "inodecache.h"

#define INO_CACHE_VERSION 1U

struct __attribute__((packed)) ino_hash {
	uint16_t version;
	uint16_t kind;
	uint32_t dev;
	uint64_t ino;
	uint64_t size;
	uint64_t mtime;
};

int inode_cache_open(struct inode_cache *cache) {
	int dirfd;
	if (cache->dirfd >= 0) {
		return 0;
	}
	if (!cache->dir) {
		return -1;
	}
	dirfd = open(cache->dir, O_PATH|O_DIRECTORY, 0);
	if (dirfd < 0) {
		return dirfd;
	}
	cache->dirfd = dirfd;
	return 0;
}

void inode_cache_close(struct inode_cache *cache) {
	close(cache->dirfd);
	cache->dirfd = -1;
}

int hash_inode(char **entry_name, const char *path, uint16_t kind) {
	int err = 0;
	struct stat st;
	struct ino_hash buf;
	char digest[MD5_DIGEST_STRING_LENGTH];

	if (stat(path, &st) != 0) {
		return -errno;
	}
	buf.version = INO_CACHE_VERSION;
	buf.kind = kind;
	buf.dev = (uint32_t)st.st_dev;
	buf.ino = (uint64_t)st.st_ino;
	buf.size = (uint64_t)st.st_size;
	buf.mtime = INT64_C(1000000)*(int64_t)(st.st_mtim.tv_sec);
       	buf.mtime += ((int64_t)(st.st_mtim.tv_nsec))/1000;

	MD5Digest((const uint8_t *)&buf, sizeof(buf), &digest);

	err = asprintf(entry_name, "%s", digest);
	if (err != -1) {
		return 0;
	} else {
		*entry_name = NULL;
		return -ENOMEM;
	}
}

static int read_entry(int fd, char *result, size_t len) {
	ssize_t bytes_read = 0;

	if (len <= 1) {
		return -EINVAL;
	}
	len -= 1; /* for a terminating NULL */

	while ((len > 0) && (bytes_read = read(fd, result, len)) > 0) {
		result += bytes_read;
		len -= bytes_read;
	}

	if (bytes_read < 0) {
		return -errno;
	} else if (0 == bytes_read) {
		/* ensure the thing is NULL terminated */
		if (result[-1] != '\0') {
			*result = '\0';
		}
		return 0;
	} else {
		/* should not happen */
		return -EXIT_FAILURE;
	}
}

static int write_entry(int fd, const char *value, size_t len) {
	ssize_t bytes_written = 0;

	while (len > 0) {
		bytes_written = write(fd, value, len);
		if (bytes_written < 0) {
			return -errno;
		}
		value += bytes_written;
		len -= bytes_written;
	}
	return 0;
}

int inode_cache_lock(int dirfd, const char *entry_name, int exclusive) {
	int fd = -1;
	int err = 0;
	char *lock_name = NULL;

	if (asprintf(&lock_name, "%s.lock", entry_name) < 0) {
		lock_name = NULL;
		fd = -ENOMEM;
		goto out;
	}
	fd = openat(dirfd, lock_name, O_WRONLY|O_TRUNC|O_CREAT, 0666);
	if (fd < 0) {
		err = -errno;
		goto out;
	}
	if (flock(fd, exclusive ? LOCK_EX : LOCK_SH) < 0) {
		err = -errno;
		goto out;
	}
out:
	free(lock_name);
	if (err) {
		if (fd >= 0) {
			close(fd);
		}
		if (err > 0) {
			err = -err;
		}
		return err;
	} else {
		return fd;
	}
}

void inode_cache_unlock(int *lockfd) {
	flock(*lockfd, LOCK_UN);
	close(*lockfd);
	*lockfd = -1;
}

int inode_cache_get(const struct inode_cache *cache, const char *path, uint16_t kind, char **result) {
	int err;
	int entry_fd = -1;
	int lock_fd = -1;
	char *entry_name = NULL;
	char val_buf[INO_CACHE_ENTRY_MAX_SIZE];

	if (!result) {
		err = -EINVAL;
		goto out;
	}
	err = hash_inode(&entry_name, path, kind);
	if (err) {
		entry_name = NULL;
		goto out;
	}

	lock_fd = inode_cache_lock(cache->dirfd, entry_name, /* exclusive = */ 0);
	if (lock_fd < 0) {
		err = lock_fd;
		goto out;
	}

	entry_fd = openat(cache->dirfd, entry_name, O_RDONLY|O_NOFOLLOW);
	if (entry_fd < 0) {
		err = -errno;
		goto out;
	}
	err = read_entry(entry_fd, val_buf, sizeof(val_buf));
	*result = strdup(val_buf);
	if (!*result) {
		err = -ENOMEM;
		goto out;
	}
out:
	if (entry_fd >= 0) {
		close(entry_fd);
	}
	if (lock_fd >= 0) {
		inode_cache_unlock(&lock_fd);
	}
	free(entry_name);
	return err;
}

int inode_cache_put(const struct inode_cache *cache, const char *path, uint16_t kind, const char *value) {
	int err = 0;
	size_t value_len = 0;
	int entry_fd = -1;
	int lock_fd = -1;
	const char *entry_name = NULL;

	if (!cache) {
		err = -EINVAL;
		goto out;
	}
	if (!path) {
		err = -EINVAL;
		goto out;
	}
	if (!value) {
		err = -EINVAL;
		goto out;
	}

	value_len = strlen(value) + 1;
	if (value_len > INO_CACHE_ENTRY_MAX_SIZE) {
		err = -E2BIG;
		goto out;
	}

	err = hash_inode((char **)&entry_name, path, kind);
	if (err) {
		entry_name = NULL;
		goto out;
	}

	lock_fd = inode_cache_lock(cache->dirfd, entry_name, /* exclusive = */ 1);
	if (lock_fd < 0) {
		err = lock_fd;
		goto out;
	}

	entry_fd = openat(cache->dirfd, entry_name, O_WRONLY|O_TRUNC|O_CREAT, 0666);
	if (entry_fd < 0) {
		err = entry_fd;
		goto out;
	}
	err = write_entry(entry_fd, value, value_len);
	if (err) {
		goto out;
	}
	if (fsync(entry_fd) < 0) {
		err = -errno;
		goto out;
	}
	if (close(entry_fd) < 0) {
		err = -errno;
		goto out;
	} else {
		entry_fd = -1;
	}
out:
	if (lock_fd >= 0) {
		inode_cache_unlock(&lock_fd);
	}
	free((void *)entry_name);
	if (entry_fd >= 0) {
		close(entry_fd);
	}
	return err;
}	

int inode_cache_del(const struct inode_cache *cache, const char *path, uint16_t kind) {
	int err = 0;
	int lock_fd = -1;
	char *entry_name= NULL;

	err = hash_inode(&entry_name, path, kind);
	if (err) {
		goto out;
	}

	lock_fd = inode_cache_lock(cache->dirfd, entry_name, /* exclusive = */ 1);
	if (lock_fd < 0) {
		err = lock_fd;
		goto out;
	}

	if (unlinkat(cache->dirfd, entry_name, 0) != 0) {
		if (ENOENT == errno) {
			err = 0;
		} else {
			err = -errno;
			goto out;
		}
	}
out:
	if (lock_fd >= 0) {
		inode_cache_unlock(&lock_fd);
	}
	free(entry_name);
	return err;
}

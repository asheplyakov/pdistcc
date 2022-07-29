#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>

#define pr_debug(format, args...) fprintf(stderr, "%s: " format "\n", __func__, args)

int mkdir_p(char *path, mode_t mode) {
	int err = 0, dirfd = -1, nextdirfd = -1;
	char *end = NULL;
	int keep_going = 1;
	if (path[0] == '/') {
		dirfd = open("/", O_PATH|O_DIRECTORY, 0);
		if (dirfd < 0) {
			err = -errno;
			pr_debug("failed to open root directory: %d (%s)", errno, strerror(errno));
			goto out;
		}
		path++;
	} else {
		dirfd = AT_FDCWD;
	}
	while (keep_going) {
		end = strchr(path, '/');
		if (!end) {
			keep_going = 0;
		} else {
			*end = '\0';
		}
		if ((nextdirfd = mkdirat(dirfd, path, mode)) < 0) {
			if (errno != EEXIST) {
				err = -errno;
				pr_debug("failed to create %s: %d (%s)", path, errno, strerror(errno));
				goto out;
			}
		}
		if ((nextdirfd = openat(dirfd, path, O_PATH|O_DIRECTORY, 0)) < 0) {
			err = -errno;
			pr_debug("%s exists and is not a directory", path);
			goto out;
		}
		close(dirfd);
		dirfd = nextdirfd;
		nextdirfd = -1;
		if (end) {
			path = end + 1;
			*end = '/';
		}
	}
out:
	if (end) {
		*end = '/';
	}
	if (nextdirfd >= 0) {
		close(nextdirfd);
	}
	if (err) {
		if (dirfd >= 0) {
			close(dirfd);
		}
		dirfd = err;
	}
	return dirfd;
}

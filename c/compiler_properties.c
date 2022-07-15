#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

size_t skip_whitespace(char * const str) {
    char *w = str, *r = str;
    size_t len = 0;
    while (*r) {
        if (isspace(*r)) {
            r++;
            continue;
        }
        if (w < r) {
            *w = *r;
        } else if (w == r) {
            /* nothing special */
        } else {
            printf("this should not happen\n");
            exit(1);
        }
        w++;
        r++;
	len++;
    }
    *w = '\0';
    return len;
}

int get_gcc_triplet(const char *compiler, char **value) {
	int err = 0;
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0;
	ssize_t len = -1;
	char *newlineptr = NULL;

	if (!value) {
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

	if ((len = getline(value, &bufsz, gccpipe)) < 0) {
		err = -errno;
		printf("%s: getline failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	err = pclose(gccpipe);
	gccpipe = NULL;
	if (err > 0) {
		printf("%s: '%s' returned %d\n", __func__, cmd, err);
		goto out;
	} else if (err < 0) {
		if (errno) {
			err = - errno;
			printf("%s: failed to run '%s', error %d (%s)\n",
				__func__, cmd, err, strerror(errno));
		} else {
			printf("%s: failed to run '%s', unknown error\n",
				__func__, cmd);
		}
		goto out;
	}

	newlineptr = strchr(*value, '\n');
	if (newlineptr) {
		*newlineptr = '\0';
	}

out:
	if (gccpipe) {
		pclose(gccpipe);
	}
	free(cmd);
	if (err && value) {
		free(*value);
		value = NULL;
	}
	return err;
}

/* gcc -march=native -Q --help=target | awk '/^\s*[-]march[=]/ { print $2 }' */
int get_march_native(const char *compiler, const char *opt, char **value) {
	int err = 0;
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0, optlen = 0;
	ssize_t len = -1;
	char *line = NULL;

	if (!value) {
		err = -EINVAL;
		goto out;
	}
	if (*value) {
		free(*value);
		*value = NULL;
	}

	if (asprintf(&cmd, "%s -%s=native -Q --help=target", compiler, opt) < 0) {
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
	optlen = strlen(opt);
	while (!feof(gccpipe) && !ferror(gccpipe)) {
		len = getline(&line, &bufsz, gccpipe);
		if (len < 0) {
			err = -errno;
			goto out;
		}
		len = skip_whitespace(line);
		/* matching line: '-march=CPUNAME' */
		if (len < 2 || line[0] != '-') {
			continue;
		}
		/* '-', '=' - 2 characters, CPUNAME - at least 1 character */
		if (len < optlen + 3 || line[optlen + 1] != '=') {
			continue;
		}
		if (strncmp(line + 1, opt, optlen) == 0) {
			*value = strdup(line + optlen + 2);
			if (!*value) {
				err = -ENOMEM;
				goto out;
			}
			break;
		}
	}
	if (!*value) {
		printf("%s: failed to guess -march=native\n", __func__);
		err = -ENOENT;
		goto out;
	}

	err = pclose(gccpipe);
	gccpipe = NULL;
	if (err > 0) {
		printf("%s: '%s' returned %d\n", __func__, cmd, err);
		goto out;
	} else if (err < 0) {
		if (errno) {
			err = -errno;
			printf("%s: failed to run '%s': error %d (%s)\n",
				__func__, cmd, errno, strerror(errno));
		} else {
			printf("%s: failed to run '%s': unknown error\n",
				__func__, cmd);
		}
		goto out;
	}
out:
	if (err && value) {
		free(*value);
		*value = NULL;
	}
	free(line);
	if (gccpipe) {
		pclose(gccpipe);
	}
	free(cmd);
	return err;
}

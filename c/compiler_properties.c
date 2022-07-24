#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>

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
	int err = 0, wstatus;
	int pipefd[2] = { -1, -1 };
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0;
	ssize_t len = -1;
	char *newlineptr = NULL;
	pid_t gccpid;

	if (!value) {
		err = -EINVAL;
		goto out;
	}
	if (pipe(pipefd) < 0) {
		err = -errno;
		printf("%s: pipe failed %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if (asprintf(&cmd, "%s -dumpmachine", compiler) < 0) {
		cmd = NULL;
		err = -ENOMEM;
		goto out;
	}

	if ((gccpid = fork()) < 0) {
		err = -errno;
		printf("%s: fork failed %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	} else if (gccpid == 0) {
		int nullfd = -1;
		char *args[] = { strdup(compiler), "-dumpmachine", NULL };
		if (!args[0]) {
			exit(ENOMEM);
		}
		signal(SIGPIPE, SIG_IGN);
		close(pipefd[0]);
		if ((nullfd = open("/dev/null", O_RDONLY)) >= 0) {
			dup2(nullfd, STDIN_FILENO);
			/* ignore errors: will use stdin of parent */
			close(nullfd);
		}
		if (dup2(pipefd[1], STDOUT_FILENO) < 0) {
			exit(errno ? errno : 125);
		}
		close(pipefd[1]);
		execv(compiler, args);
		exit(errno ? errno : 126);
	}

	close(pipefd[1]);
	pipefd[1] = -1;
	gccpipe = fdopen(pipefd[0], "r");
	if (!gccpipe) {
		err = errno ? -errno : -ENOMEM;
		printf("%s: fdopen failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if (*value) {
		free(*value);
		*value = NULL;
	}

	if ((len = getline(value, &bufsz, gccpipe)) < 0) {
		err = -errno;
		printf("%s: getline failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if (waitpid(gccpid, &wstatus, 0) < 0) {
		err = -errno;
		printf("%s: waitpid failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if (WIFEXITED(wstatus)) {
		err = WEXITSTATUS(wstatus);
		if (err) {
			printf("%s: '%s' has returned non-zero code %d\n", __func__, cmd, err);
			goto out;
		}
	} else if (WIFSIGNALED(wstatus)) {
		err = WTERMSIG(wstatus);
		printf("%s: '%s' was killed by signal %d\n", __func__, cmd, err);
		goto out;
	} else {
		printf("%s: unexpected wstatus %d, bailing out\n", __func__, wstatus);
		err = -EINVAL;
		goto out;
	}

	newlineptr = strchr(*value, '\n');
	if (newlineptr) {
		*newlineptr = '\0';
	}

out:
	if (gccpipe) {
		fclose(gccpipe);
		pipefd[0] = -1;
	}
	if (pipefd[0] >= 0) {
		close(pipefd[0]);
		pipefd[0] = -1;
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
	int pipefd[2] = { -1, -1 };
	int err = 0, wstatus;
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0, optlen = 0;
	ssize_t len = -1;
	char *line = NULL;
	pid_t gccpid;

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

	if (pipe(pipefd) < 0) {
		err = -errno;
		printf("%s: pipe failed %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}
	if ((gccpid = fork()) < 0) {
		err = -errno;
		printf("%s: fork failed %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	} else if (gccpid == 0) {
		int nullfd = -1;
		char *args[] = { strdup(compiler), NULL, "-Q", "--help=target", NULL };
		if (!args[0]) {
			exit(ENOMEM);
		}
		if (asprintf(&args[1], "-%s=native", opt) < 0) {
			exit(ENOMEM);
		}
		/* we are not going to read the whole output, so suppress SIGPIPE */
		signal(SIGPIPE, SIG_IGN);
		close(pipefd[0]);
		if ((nullfd = open("/dev/null", O_RDONLY)) >= 0) {
			dup2(nullfd, STDIN_FILENO);
			/* On error: use the stdin of parent */
			close(nullfd);
		}
		if (dup2(pipefd[1], STDOUT_FILENO) < 0) {
			exit(errno ? errno : 125);
		}
		close(pipefd[1]);
		execv(compiler, args);
		exit(errno ? errno : 126);
	}
	close(pipefd[1]);
	gccpipe = fdopen(pipefd[0], "r");

	if (!gccpipe) {
		err = errno ? -errno : -ENOMEM;
		printf("%s: fdopen failed: %d (%s)\n", __func__, errno, strerror(errno));
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

	if (waitpid(gccpid, &wstatus, 0) < 0) {
		err = -errno;
		printf("%s: waitpid failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if (WIFEXITED(wstatus)) {
		err = WEXITSTATUS(wstatus);
		if (err) {
			printf("%s: '%s' has returned non-zero status %d\n", __func__, cmd, err);
			goto out;
		}
	} else if (WIFSIGNALED(wstatus)) {
		err = WTERMSIG(wstatus);
		printf("%s: '%s' was killed by signal %d\n", __func__, cmd, err);
		goto out;
	} else {
		err = -EINVAL;
		printf("%s: '%s': unexpected wstatus %d\n", __func__, cmd, wstatus);
		goto out;
	}

	if (!*value) {
		printf("%s: failed to guess -march=native\n", __func__);
		err = -ENOENT;
		goto out;
	}

out:
	if (err && value) {
		free(*value);
		*value = NULL;
	}
	if (gccpipe) {
		fclose(gccpipe);
		pipefd[0] = -1;
	}
	if (pipefd[0] >= 0) {
		close(pipefd[0]);
		pipefd[0] = -1;
	}
	free(line);
	free(cmd);
	return err;
}

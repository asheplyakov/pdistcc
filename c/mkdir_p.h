#ifndef SA_MKDIR_P_H
#define SA_MKDIR_P_H
#include <sys/types.h>

/* @brief Create and open a directory
 *
 * Creates parent directories if necessary.
 *
 * @param path directory path, either relative or absolute
 * @param mode permissions of newly created directories
 * @return if successful - the file descriptor of the newly created
 *         (opened), otherwise the negated errno
 * @note Modifies the @var{path} during execution
 */
extern int mkdir_p(char *path, mode_t mode);

#endif /* SA_MKDIR_P_H */

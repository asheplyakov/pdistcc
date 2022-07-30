#ifndef COMPILER_PROPERTIES_H
#define COMPILER_PROPERTIES_H

/**
 * @brief Figure out GCC triplet.
 *
 * @param compiler path to the compiler.
 * @param valueptr pointer to triplet string, will be set by this function.
 * @return 0 on success something else on error
 *
 * @note: @var{valueptr} is heap allocated and must be released
 *        by the caller (with `free`).
 * @note: on error @var{valueptr} is reset to NULL.
 */
extern int get_gcc_triplet(const char *compiler, char **valueptr);

/**
 * @brief Guess the actual CPU name for -march=native
 *
 * @param compiler path to the compiler
 * @param valueptr pointer to CPU name, will be set by this function.
 * @return 0 on success something else on error
 *
 * @note: @var{valueptr} is heap allocated and must be released
 *        by the caller (with `free`).
 * @note: on error @var{valueptr} is reset to NULL.
 */
extern int get_march_native(const char *compiler, const char *opt, char **valueptr);

enum GCC_PROPERTIES {
	GCC_TRIPLET = 1,
	GCC_MARCH_NATIVE = 2,
};

#endif


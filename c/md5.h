/*	$OpenBSD: md5.h,v 1.15 2004/05/03 17:30:14 millert Exp $	*/

/*
 * This code implements the MD5 message-digest algorithm.
 * The algorithm is due to Ron Rivest.  This code was
 * written by Colin Plumb in 1993, no copyright is claimed.
 * This code is in the public domain; do with it what you wish.
 *
 * Equivalent code is available from RSA Data Security, Inc.
 * This code has been tested against that, and is equivalent,
 * except that you don't need to include two pages of legalese
 * with every copy.
 */

/*
 * this file has been downloaded from
 * https://git.hadrons.org/cgit/libmd.git/plain/include/md5.h?id=9d3c9a739f86b65b238163b9f8af3623226a6419
 */

#ifndef _MD5_H_
#define _MD5_H_

#include <sys/types.h>

#include <stdint.h>

#define	MD5_BLOCK_LENGTH		64
#define	MD5_DIGEST_LENGTH		16
#define	MD5_DIGEST_STRING_LENGTH	(MD5_DIGEST_LENGTH * 2 + 1)

typedef struct MD5Context {
	uint32_t state[4];			/* state */
	uint64_t count;				/* number of bits, mod 2^64 */
	uint8_t buffer[MD5_BLOCK_LENGTH];	/* input buffer */
} MD5_CTX;

#ifdef __cplusplus
extern "C" {
#endif

void	 MD5Init(MD5_CTX *);
void	 MD5Update(MD5_CTX *, const uint8_t *, size_t);
void	 MD5Pad(MD5_CTX *);
void	 MD5Final(uint8_t [MD5_DIGEST_LENGTH], MD5_CTX *);
void	 MD5Transform(uint32_t [4], const uint8_t [MD5_BLOCK_LENGTH]);
void	 MD5Digest(const uint8_t *, size_t, char (*)[MD5_DIGEST_STRING_LENGTH]);

#ifdef __cplusplus
}
#endif

#endif /* _MD5_H_ */

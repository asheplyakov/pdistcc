#ifndef DCC_INODE_CACHE_H
#define DCC_INODE_CACHE_H

#include <stdint.h>


struct inode_cache {
	const char *dir;
	int dirfd;
};

extern int inode_cache_open(struct inode_cache *cache);
extern void inode_cache_close(struct inode_cache *cache);

extern int inode_cache_get(const struct inode_cache *cache,
			   const char *path,
			   uint16_t kind,
			   char **value);

extern int inode_cache_put(const struct inode_cache *cache,
			   const char *path,
			   uint16_t kind,
			   const char *value);

extern int inode_cache_del(const struct inode_cache *cache,
			   const char *path,
			   uint16_t kind);

#define INO_CACHE_ENTRY_MAX_SIZE 512U

#endif /* DCC_INODE_CACHE_H */


package main

import (
	"fmt"
	"github.com/asheplyakov/pdistcc/pkg/dccclient"
	"os"
)

func main() {
	src := os.Args[1]
	obj := os.Args[2]
	server := os.Args[3]
	args := os.Args[4:]
	status, err := dccclient.DccCompile(args, src, obj, server)
	if err != nil {
		fmt.Println("internal error", err)
		os.Exit(1)
	}
	os.Exit(status)
}

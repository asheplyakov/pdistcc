package client

import (
	"fmt"
	"io"
	"log"
	"strconv"
)

const (
	TOKEN_LEN      int = 12
	TOKEN_NAME_LEN int = 4
)

type DccClient struct {
	version int
	rsock   io.Reader
	wsock   io.Writer
	stdout  io.Writer
	stderr  io.Writer
	doti    io.Reader
	dotilen int
	ofile   io.Writer
}

func DccEncode(token string, val int) string {
	var tok [4]byte
	copy(tok[:], token)
	return fmt.Sprintf("%s%08x", string(tok[:]), val)
}

func DccEncodeString(token string, val string) string {
	var tok [4]byte
	copy(tok[:], token)
	return fmt.Sprintf("%s%08x%s", string(tok[:]), len(val), val)
}

func sendToken(sock io.Writer, token string, val int) (err error) {
	var n int
	n, err = io.WriteString(sock, DccEncode(token, val))
	if err != nil {
		log.Println("Failed to send:", err)
		return
	}
	if n != TOKEN_LEN {
		err = fmt.Errorf("Failed to send: expected: %d bytes, actual: %d", TOKEN_LEN, n)
		log.Println(err)
		return
	}
	return
}

func readToken(sock io.Reader, token string) (val int, err error) {
	var (
		buf   [TOKEN_LEN]byte
		n     int
		value int64
	)
	if n, err = io.ReadFull(sock, buf[:]); err != nil {
		log.Println(err)
		return
	}
	if n != TOKEN_LEN {
		err = fmt.Errorf("failed to read %d bytes", TOKEN_LEN)
		return
	}
	t := string(buf[:4])
	if token != t {
		err = fmt.Errorf("wrong token: expected: %s, got: %s", token, t)
		return
	}
	if value, err = strconv.ParseInt(string(buf[4:]), 16, 32); err != nil {
		log.Println(err)
		return
	}
	val = int(value)
	return
}

func sendStringToken(sock io.Writer, token string, val string) (err error) {
	var n int
	encoded := DccEncodeString(token, val)
	n, err = io.WriteString(sock, encoded)
	if err != nil {
		log.Println("Failed to send:", err)
		return
	}
	if n != len(encoded) {
		err = fmt.Errorf("Failed to send: expected %d bytes, actual: %d", len(encoded), n)
		log.Println(err)
		return
	}
	return
}

func (c *DccClient) Request(args []string) (err error) {
	var sz int64
	err = sendToken(c.wsock, "DIST", c.version)
	if err != nil {
		return
	}
	err = sendToken(c.wsock, "ARGC", len(args))
	if err != nil {
		return
	}
	for i, arg := range args {
		err = sendStringToken(c.wsock, "ARGV", arg)
		if err != nil {
			log.Println("Failed to send arg", i)
			return
		}
	}
	err = sendToken(c.wsock, "DOTI", c.dotilen)
	if err != nil {
		return
	}
	sz, err = io.Copy(c.wsock, c.doti)
	if err != nil {
		return
	}
	if sz != int64(c.dotilen) {
		err = fmt.Errorf("Failed to send DOTI file")
		log.Println("Failed to send DOTI file")
		return
	}
	return
}

func readTokenTo(sock io.Reader, name string, w io.Writer) (err error) {
	var (
		size int
	)
	if size, err = readToken(sock, name); err != nil {
		err = fmt.Errorf("haven't got a valid %s token: %v", name, err)
		return
	}
	if _, err = io.CopyN(w, sock, int64(size)); err != nil {
		err = fmt.Errorf("Failed to receive %s: error: %v", name, err)
		return
	}
	return
}

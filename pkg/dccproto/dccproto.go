package dccproto

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

func SendToken(sock io.Writer, token string, val int) (err error) {
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

func ReadToken(sock io.Reader, token string) (val int, err error) {
	var (
		buf   [TOKEN_LEN]byte
		n     int
		value int64
	)
	if n, err = io.ReadFull(sock, buf[:]); err != nil {
		if n != TOKEN_LEN {
			log.Printf("ReadToken: short read: %d bytes of %d", n, TOKEN_LEN)
		} else {
			log.Println("ReadToken: error:", err)
		}
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

func ReadTokenTo(sock io.Reader, name string, w io.Writer) (err error) {
	var (
		size int
	)
	if size, err = ReadToken(sock, name); err != nil {
		err = fmt.Errorf("haven't got a valid %s token: %v", name, err)
		return
	}
	if _, err = io.CopyN(w, sock, int64(size)); err != nil {
		err = fmt.Errorf("Failed to receive %s: error: %v", name, err)
		return
	}
	return
}

func SendStringToken(sock io.Writer, token string, val string) (err error) {
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

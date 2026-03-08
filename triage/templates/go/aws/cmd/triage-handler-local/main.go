package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
)

func main() {
	cloud := flag.String("cloud", "aws", "cloud name")
	inputPath := flag.String("input", "-", "input file or - for stdin")
	flag.Parse()

	var payload []byte
	var err error
	if *inputPath == "-" {
		payload, err = io.ReadAll(os.Stdin)
	} else {
		payload, err = os.ReadFile(*inputPath)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	result := map[string]any{
		"handler":        "triage-handler",
		"runtime":        "go",
		"cloud":          *cloud,
		"entrypoint":     "cmd/triage-handler-local",
		"payload_length": len(payload),
	}

	encoded, err := json.Marshal(result)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	fmt.Println(string(encoded))
}

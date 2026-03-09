package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"

	"triage-handler/internal/runtime"
)

func main() {
	cloud := flag.String("cloud", "gcp", "cloud name")
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

	summary := runtime.NewReplaySummary(*cloud, "cmd/triage-handler-local", payload, "", "")

	encoded, err := json.Marshal(summary)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	fmt.Println(string(encoded))
}

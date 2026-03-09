package main

import (
	"log"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"

	adapter "triage-handler/internal/adapters/gcp"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	router := chi.NewRouter()
	router.Get("/healthz", adapter.Healthz)
	router.Post("/", adapter.HandlePush)

	address := ":" + port
	log.Printf("triage-handler listening on %s", address)
	if err := http.ListenAndServe(address, router); err != nil {
		log.Fatal(err)
	}
}

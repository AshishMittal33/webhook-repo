# Webhook Repo

This repository contains a Flask application that receives GitHub webhook events and displays them in a web UI.

## What it does
- Receives GitHub webhooks
- Handles PUSH, PR, and MERGE events
- Displays events in a browser table
- Auto-refreshes every few seconds

## How to run

python app.py

App runs at:

http://localhost:5000

ngrok To receive GitHub webhooks locally:

ngrok http 5000

Use the generated URL in GitHub webhook settings:

https://<ngrok-url>/webhook

## Endpoints

- /webhook → Receives GitHub events

- /events → Returns stored events

- / → UI to view events

## Connection

This repo receives events from action-repo via GitHub Webhooks.

## Notes

- Uses in-memory storage

- Data resets on restart

- ngrok URL changes every time

## Demo

https://youtu.be/f2GTOpM8ueA


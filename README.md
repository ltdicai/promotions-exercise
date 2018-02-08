# Promotions exercise

## Installing and running

Run `source ./install.sh` and it will automatically create a virtualenv and install dependencies

Run `./run.sh` to start the app.

Don't forget to run `deactivate` when done!

## Available endpoints

- `GET /`
Get index with links to available endpoints

- `GET /promotions`
List all promotions currently on DB


- `GET /promotions?json`
Return a json containing all promotions currently on DB

- `GET /promotions/upload`
This takes you to a page with a file input so you can upload a file with promotions.
Importing a .json file is fully implemented and importing a .csv will load 3 mock promotions


- `POST /promotions/upload {"fileURL": <fileURL>, "fileType": <fileType>}`
Using cURL you can upload a file using a `fileURL` and a `fileType` (`"csv"` or `"json"` so far).
For example, use http://myjson.com/ to generate a public link and upload it with `"fileType":"json"`


- `GET /clear`
Empty DB so you can import the example promotions again


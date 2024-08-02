# README

This is the [Flask](http://flask.pocoo.org/) [quick start](http://flask.pocoo.org/docs/1.0/quickstart/#a-minimal-application) example for [Render](https://render.com).

The app in this repo is deployed at [https://flask.onrender.com](https://flask.onrender.com).

## Deployment

Follow the guide at https://render.com/docs/deploy-flask.

## Running the Manual Script

To run the script for creating a new Pinecone index, you can use the following command:

`python scripts/create_pinecone_index.py <index_name> <dimension>`

## Update Post and Reply Database

For Post please run this command:
`python scripts/save_post.py`

For comments run this command:
`python scripts/save_reply.py`

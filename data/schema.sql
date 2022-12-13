-- This is the schema for the database, data.db (SQLite)
-- Run this file's code in a SQLite database to create the tables

-- Table: playlists
CREATE TABLE "playlists" (
	"id"	TEXT NOT NULL UNIQUE,
	"author"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"visibility"	INTEGER NOT NULL DEFAULT 0 CHECK("visibility" == 0 OR "visibility" == 1),
	"listens"	INTEGER NOT NULL DEFAULT 0 CHECK("listens" >= 0),
	PRIMARY KEY("id")
);


-- Table: playlist_data
CREATE TABLE "playlist_data" (
	"id"	TEXT NOT NULL,
	"song"	TEXT NOT NULL
);


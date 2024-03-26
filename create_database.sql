CREATE DATABASE netstests;
USE networks_tests;

CREATE TABLE networks_tests (
    test_time TIMESTAMP NOT NULL,
    name VARCHAR(500) NOT NULL,
    code VARCHAR(10) NOT NULL,
    doi_result BOOLEAN NOT NULL,
    doi_comment VARCHAR(500),
    page_result BOOLEAN NOT NULL,
    open_result BOOLEAN NOT NULL,
    license_result BOOLEAN NOT NULL,
    license_comment VARCHAR(500),
    publisher VARCHAR(500),
    stationxml_result BOOLEAN NOT NULL,
    stationxml_comment VARCHAR(1000),
    PRIMARY KEY (test_time, name)
);

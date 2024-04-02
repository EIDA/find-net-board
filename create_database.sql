CREATE DATABASE netstests;
USE netstests;

CREATE TABLE networks_tests (
    test_time TIMESTAMP NOT NULL,
    name VARCHAR(500) NOT NULL,
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    enddate DATE,
    doi_result BOOLEAN NOT NULL,
    doi_comment VARCHAR(500),
    page_result BOOLEAN,
    license_result BOOLEAN,
    license_comment VARCHAR(500),
    publisher VARCHAR(500),
    datacenter VARCHAR(30),
    stationxml_result BOOLEAN,
    stationxml_comment VARCHAR(1000),
    PRIMARY KEY (test_time, name)
);

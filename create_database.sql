CREATE DATABASE netstests;
USE netstests;

CREATE TABLE networks_tests (
    test_time TIMESTAMP NOT NULL,
    name VARCHAR(500) NOT NULL,
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    enddate DATE,
    doi VARCHAR(100),
    page_result BOOLEAN,
    license VARCHAR(500),
    publisher VARCHAR(300),
    datacenter VARCHAR(30),
    stationxml_result BOOLEAN,
    stationxml_comment VARCHAR(300),
    PRIMARY KEY (test_time, name)
);


/* PROPOSED MODEL
CREATE TABLE fdsn_networks (
    name VARCHAR(500) NOT NULL,
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    enddate DATE,
    doi VARCHAR(100),
    PRIMARY KEY (code, startdate)
);

CREATE TABLE fdsn_datacenters (
    datacenter VARCHAR(30) NOT NULL,
    network VARCHAR(10) NOT NULL,
    starttime TIMESTAMP NOT NULL,
    endtime TIMESTAMP,
    PRIMARY KEY (network, starttime)
);

CREATE TABLE stationxml (
    network VARCHAR(10) NOT NULL,
    starttime TIMESTAMP NOT NULL,
    doi VARCHAR(100),
    restriction VARCHAR(50),
    PRIMARY KEY (network, starttime),
    FOREIGN KEY (network, starttime) REFERENCES fdsn_datacenters(network, starttime)
);

CREATE TABLE tests (
    test_time TIMESTAMP NOT NULL,
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    doi VARCHAR(100),
    page_result BOOLEAN,
    license VARCHAR(500),
    publisher VARCHAR(300),
    datacenter VARCHAR(30),
    stationxml_doi BOOLEAN,
    stationxml_restriction BOOLEAN,
    PRIMARY KEY (test_time, code, startdate)
    FOREIGN KEY (code, startdate) REFERENCES fdsn_networks(code, startdate)
);
*/

CREATE DATABASE networks_tests;
USE networks_tests;

CREATE TABLE networks (
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    enddate DATE,
    doi VARCHAR(100),
    PRIMARY KEY (code, startdate)
);

CREATE TABLE datacite (
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    licenses VARCHAR(500),
    page VARCHAR(300),
    publisher VARCHAR(300),
    PRIMARY KEY (code, startdate),
    FOREIGN KEY (code, startdate) REFERENCES networks(code, startdate)
);

CREATE TABLE datacenters (
    name VARCHAR(30) NOT NULL,
    station_url VARCHAR(300),
    PRIMARY KEY (name)
);

CREATE TABLE routing (
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    datacenter VARCHAR(30) NOT NULL,
    priority INT,
    source ENUM('EIDA', 'FDSN'),
    PRIMARY KEY (code, startdate, datacenter),
    FOREIGN KEY (code, startdate) REFERENCES networks(code, startdate),
    FOREIGN KEY (datacenter) REFERENCES datacenters(name)
);

CREATE TABLE stationxml (
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    doi VARCHAR(100),
    restriction VARCHAR(50),
    PRIMARY KEY (code, startdate),
    FOREIGN KEY (code, startdate) REFERENCES networks(code, startdate)
);

CREATE TABLE tests (
    test_time TIMESTAMP NOT NULL,
    code VARCHAR(10) NOT NULL,
    startdate DATE NOT NULL,
    doi VARCHAR(100),
    page_works BOOLEAN,
    has_license BOOLEAN,
    xml_doi_match BOOLEAN,
    xml_restriction_match BOOLEAN,
    PRIMARY KEY (test_time, code, startdate),
    FOREIGN KEY (code, startdate) REFERENCES networks(code, startdate)
);

--
-- PostgreSQL database dump
--

\restrict XRIHBtHWOjUyC0QelxxnmdeIDXw6iugtC8ADkWs5psgnjUjHpEGBD3XXjEy01aT

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-05-07 17:29:39

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 4 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- TOC entry 5044 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 859 (class 1247 OID 24676)
-- Name: place_tag; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.place_tag AS ENUM (
    'restaurant',
    'bakery',
    'store',
    'cafe',
    'meat',
    'dairy',
    'parve'
);


ALTER TYPE public.place_tag OWNER TO postgres;

--
-- TOC entry 871 (class 1247 OID 24715)
-- Name: verification_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.verification_status AS ENUM (
    'verified',
    'pending',
    'unverified'
);


ALTER TYPE public.verification_status OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 24706)
-- Name: hechsheraliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hechsheraliases (
    hechsherid character(11),
    hechsheralias character varying(50)
);


ALTER TABLE public.hechsheraliases OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24699)
-- Name: hechshers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hechshers (
    hechsherid character(11) NOT NULL,
    hechsherdisplayname character varying(50) NOT NULL,
    hechshersymbol character varying(255)
);


ALTER TABLE public.hechshers OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 24721)
-- Name: placehechshers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.placehechshers (
    placeid character(11),
    hechsherid character(11),
    placehechshermarkingverity public.verification_status
);


ALTER TABLE public.placehechshers OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24668)
-- Name: places; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.places (
    placeid character(11) NOT NULL,
    placename character varying(50) NOT NULL,
    coordinates character varying(50),
    streetaddress character varying(255),
    dateadded date
);


ALTER TABLE public.places OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 24691)
-- Name: placetags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.placetags (
    placeid character(11),
    placetag public.place_tag
);


ALTER TABLE public.placetags OWNER TO postgres;

--
-- TOC entry 5037 (class 0 OID 24706)
-- Dependencies: 222
-- Data for Name: hechsheraliases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.hechsheraliases (hechsherid, hechsheralias) FROM stdin;
\.


--
-- TOC entry 5036 (class 0 OID 24699)
-- Dependencies: 221
-- Data for Name: hechshers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.hechshers (hechsherid, hechsherdisplayname, hechshersymbol) FROM stdin;
\.


--
-- TOC entry 5038 (class 0 OID 24721)
-- Dependencies: 223
-- Data for Name: placehechshers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.placehechshers (placeid, hechsherid, placehechshermarkingverity) FROM stdin;
\.


--
-- TOC entry 5034 (class 0 OID 24668)
-- Dependencies: 219
-- Data for Name: places; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.places (placeid, placename, coordinates, streetaddress, dateadded) FROM stdin;
\.


--
-- TOC entry 5035 (class 0 OID 24691)
-- Dependencies: 220
-- Data for Name: placetags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.placetags (placeid, placetag) FROM stdin;
\.


--
-- TOC entry 4880 (class 2606 OID 24705)
-- Name: hechshers hechshers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hechshers
    ADD CONSTRAINT hechshers_pkey PRIMARY KEY (hechsherid);


--
-- TOC entry 4878 (class 2606 OID 24674)
-- Name: places places_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.places
    ADD CONSTRAINT places_pkey PRIMARY KEY (placeid);


--
-- TOC entry 4882 (class 2606 OID 24735)
-- Name: hechshers unique_display_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hechshers
    ADD CONSTRAINT unique_display_name UNIQUE (hechsherdisplayname);


--
-- TOC entry 4884 (class 2606 OID 24709)
-- Name: hechsheraliases fk_hechsherid; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hechsheraliases
    ADD CONSTRAINT fk_hechsherid FOREIGN KEY (hechsherid) REFERENCES public.hechshers(hechsherid);


--
-- TOC entry 4885 (class 2606 OID 24729)
-- Name: placehechshers fk_hechsherid; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.placehechshers
    ADD CONSTRAINT fk_hechsherid FOREIGN KEY (hechsherid) REFERENCES public.hechshers(hechsherid);


--
-- TOC entry 4886 (class 2606 OID 24724)
-- Name: placehechshers fk_placeid; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.placehechshers
    ADD CONSTRAINT fk_placeid FOREIGN KEY (placeid) REFERENCES public.places(placeid);


--
-- TOC entry 4883 (class 2606 OID 24694)
-- Name: placetags fk_placeid; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.placetags
    ADD CONSTRAINT fk_placeid FOREIGN KEY (placeid) REFERENCES public.places(placeid);


-- Completed on 2026-05-07 17:29:39

--
-- PostgreSQL database dump complete
--

\unrestrict XRIHBtHWOjUyC0QelxxnmdeIDXw6iugtC8ADkWs5psgnjUjHpEGBD3XXjEy01aT


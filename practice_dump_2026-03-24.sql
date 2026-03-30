--
-- PostgreSQL database dump
--

\restrict WCkxNM1kJ8UegUXoCRaFsKPB5fCB0U2g62gGOldvKQnnCkKwuHJBP5pUPTgEcmh

-- Dumped from database version 14.22 (Debian 14.22-1.pgdg13+1)
-- Dumped by pg_dump version 14.22 (Debian 14.22-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: entry_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.entry_log (
    user_id integer NOT NULL,
    date_time timestamp(2) with time zone DEFAULT now() NOT NULL,
    entry_source text NOT NULL,
    CONSTRAINT source_check CHECK ((entry_source = ANY (ARRAY['web'::text, 'tg'::text])))
);


ALTER TABLE public.entry_log OWNER TO postgres;

--
-- Name: queries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.queries (
    user_id integer NOT NULL,
    operation_type text NOT NULL,
    photo_name text NOT NULL,
    query_result numeric(10,2) NOT NULL,
    sent timestamp(2) with time zone DEFAULT now() NOT NULL,
    query_id integer NOT NULL,
    CONSTRAINT type_check CHECK ((operation_type = ANY (ARRAY['money'::text, 'object'::text])))
);


ALTER TABLE public.queries OWNER TO postgres;

--
-- Name: queries_query_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.queries ALTER COLUMN query_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.queries_query_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sessions (
    user_id integer NOT NULL,
    token text NOT NULL,
    created_at timestamp(2) with time zone DEFAULT now() NOT NULL,
    expires_at timestamp(2) with time zone
);


ALTER TABLE public.sessions OWNER TO postgres;

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    user_id integer NOT NULL,
    task_id text NOT NULL,
    original_name text NOT NULL,
    status text NOT NULL,
    result_total numeric(10,2),
    result_image text,
    created_at timestamp(2) with time zone DEFAULT now() NOT NULL,
    completed_at timestamp(2) with time zone,
    CONSTRAINT tasks_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'STARTED'::text, 'SUCCESS'::text, 'FAILURE'::text])))
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    root text DEFAULT 'common'::text NOT NULL,
    login text NOT NULL,
    directory text NOT NULL,
    password text NOT NULL,
    created timestamp(2) with time zone DEFAULT now() NOT NULL,
    tg_uuid text,
    token_balance integer DEFAULT 100 NOT NULL,
    CONSTRAINT root_value CHECK ((root = ANY (ARRAY['admin'::text, 'common'::text])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: entry_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.entry_log (user_id, date_time, entry_source) FROM stdin;
\.


--
-- Data for Name: queries; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.queries (user_id, operation_type, photo_name, query_result, sent, query_id) FROM stdin;
19	money	admin.jpg	15.67	2026-03-14 15:09:33.17+00	7
21	money	5c9f8cb0-3166-4678-921f-52caa2c6795a.jpg	22.00	2026-03-16 08:10:39.42+00	12
21	money	45131835-cac3-4b32-814d-824bcf43bb72.jpg	22.00	2026-03-16 08:14:39.12+00	13
23	money	08959fbf-27fe-48c4-b24e-c966a83909e6.jpg	22.00	2026-03-16 08:23:58.39+00	14
21	money	fdde53ce-c2eb-4ed7-9909-0adfa41c9968.jpg	21.00	2026-03-17 09:01:36.35+00	15
21	money	d5c9b8ff-e7eb-428c-856b-f68aab6115a9.jpg	21.00	2026-03-17 09:18:09.3+00	16
23	money	48e062c9-4d8d-4cb7-92fd-a65e4ec2e8ff.jpg	2039.00	2026-03-17 09:19:59.17+00	17
21	money	da5d8ce7-034b-4274-a695-c6e9e5cc7523.jpg	1073.00	2026-03-17 11:33:50.06+00	18
21	money	f88676d7-25e6-4a39-a6ee-f5d6874da2d2.jpg	5.00	2026-03-22 06:43:56.43+00	19
21	money	81656ab9-b97a-41ab-8dae-5c2c2ce271d5.jpg	5.00	2026-03-22 06:44:12.06+00	20
19	money	535c3def-5e32-4a3e-93ac-ddfc60b87334.jpg	5.00	2026-03-22 06:47:32.58+00	21
19	money	363d4501-27f5-4494-b055-73cfb6611553.jpg	5.00	2026-03-24 07:25:11.39+00	22
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sessions (user_id, token, created_at, expires_at) FROM stdin;
21	W3qTSm2c8eRADLMfuUel-LYgT1kcooFnzDwFwzzTi_s	2026-03-16 07:43:40.58+00	\N
21	C0v8NwLlgHcOrzRGrMgugPIhHCzWPCzgpKRohMa4vzY	2026-03-16 08:02:23.65+00	\N
21	oTSpGyE9yj5kpqBGk-4ihGrMyNGmrzKR7ueuY_uxzAo	2026-03-16 08:02:31.25+00	\N
21	4gHwBNoo1UBeyofJ-p_gbB0LKcnEBLSKHVPmngrpFRw	2026-03-16 08:10:02.32+00	\N
21	BixWJKmV22AOohOkcdrDRibv7HANXVRT9SZp45-_CXg	2026-03-16 08:12:15.79+00	\N
23	3i2Rb4LSI_1C1shuryvIy1oKoFg7W_A-Zn6CX9qojlE	2026-03-16 08:16:14.06+00	\N
21	sBWpB7H-QoI714f7vN5JM4DJY5idk9JjXpBR-yzFGsk	2026-03-16 08:29:58.32+00	\N
21	u_1um9fRjHj6bBn4_11_stgpnFuC6mEJf8kav_pRUZs	2026-03-16 08:39:14.63+00	\N
21	dqC-e7o2bDnHTbUJbThLP3N9PoZ6gjrMXVcO9nhBxRk	2026-03-17 09:00:12.32+00	\N
21	rzZE9spicU45RfLXqx66ZsXkKzHb3CozjE9F2l9ZVSA	2026-03-17 09:12:12.86+00	\N
21	Vm3YN0bAgYjgOuQL4FVZHWZN2jQdX1wUJ_ONzfpWVfs	2026-03-20 07:02:53.2+00	\N
19	pi9zuQfcWQlTJIM9rzwaJ-5PZ3fi-_SS_DgSn1Yy8JY	2026-03-21 18:39:29.95+00	\N
21	4GHHlHrmc0pxQ8k3dIdguVo9CNC_VFd8L4580kHKIhI	2026-03-21 18:39:29.97+00	\N
19	TuWYGsyQ4Ub_wA3wOpb9OV_MFf5L2y-ab1OM23Vwf4U	2026-03-21 18:40:05.36+00	\N
21	8C1P3SfZuHneIUPe_RnyYoAE5O7QOER3c466EgzoBI0	2026-03-21 18:49:35.1+00	\N
21	PGemQMwdjucaWUzzPHmeJ0zOA7vVaZ8qE3vy3qAuCAw	2026-03-21 18:52:01.96+00	\N
21	8HpzG5lQURa0-4HcZ-ep14fi7a7Pj0Kj73BX5N_YyDM	2026-03-22 06:41:13.75+00	\N
21	ZKoJ3Ij79S5Q-mH8GCuGryBj9tOw76AdeZcPo3wQR98	2026-03-22 06:43:46.78+00	\N
19	hnsO6m2_B4VTR0QYLUd897HYrBr8NH584TWfYfFPnrU	2026-03-23 19:53:06.54+00	\N
19	Nzx8ql-MxPn-z17X72M2ot8_GyU5q4VafrnWDjx7Kic	2026-03-24 07:18:27.04+00	\N
19	KPw0qwOrP-oYgBo6q3lPLUf2N9bw4awRlzwAfbqshgA	2026-03-24 07:18:42.79+00	\N
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tasks (user_id, task_id, original_name, status, result_total, result_image, created_at, completed_at) FROM stdin;
21	d89af451-2ee1-4eea-b740-cbb6cb3f4dc6	photo_2026-03-13_14-08-42.jpg	PENDING	\N	\N	2026-03-16 07:36:54.57+00	\N
21	5c9f8cb0-3166-4678-921f-52caa2c6795a	photo_2026-03-14_09-19-12.jpg	SUCCESS	22.00	5c9f8cb0-3166-4678-921f-52caa2c6795a.jpg	2026-03-16 08:10:14.48+00	2026-03-16 08:10:39.43+00
21	45131835-cac3-4b32-814d-824bcf43bb72	photo_2026-03-14_09-19-12.jpg	SUCCESS	22.00	45131835-cac3-4b32-814d-824bcf43bb72.jpg	2026-03-16 08:14:23.83+00	2026-03-16 08:14:39.13+00
23	08959fbf-27fe-48c4-b24e-c966a83909e6	photo_2026-03-14_09-19-12.jpg	SUCCESS	22.00	08959fbf-27fe-48c4-b24e-c966a83909e6.jpg	2026-03-16 08:23:43.82+00	2026-03-16 08:23:58.44+00
21	fdde53ce-c2eb-4ed7-9909-0adfa41c9968	photo_2026-03-14_09-19-11.jpg	SUCCESS	21.00	fdde53ce-c2eb-4ed7-9909-0adfa41c9968.jpg	2026-03-17 09:00:39.61+00	2026-03-17 09:01:36.35+00
21	d5c9b8ff-e7eb-428c-856b-f68aab6115a9	photo_2026-03-14_09-19-11.jpg	SUCCESS	21.00	d5c9b8ff-e7eb-428c-856b-f68aab6115a9.jpg	2026-03-17 09:17:50.63+00	2026-03-17 09:18:09.3+00
23	48e062c9-4d8d-4cb7-92fd-a65e4ec2e8ff	2026-03-11 18-13-16.JPG	SUCCESS	2039.00	48e062c9-4d8d-4cb7-92fd-a65e4ec2e8ff.jpg	2026-03-17 09:19:43.19+00	2026-03-17 09:19:59.17+00
21	da5d8ce7-034b-4274-a695-c6e9e5cc7523	2026-03-11 18-13-00.JPG	SUCCESS	1073.00	da5d8ce7-034b-4274-a695-c6e9e5cc7523.jpg	2026-03-17 11:32:57.82+00	2026-03-17 11:33:50.06+00
19	aed68c6f-3ce9-42fe-a703-fc5934a5b42c	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	PENDING	\N	\N	2026-03-21 18:40:31.85+00	\N
21	71e6d58b-86e4-4bc6-b8b8-f43ed4266223	82a543e316c8440e9e0aa5022ff1662a.jpg	FAILURE	\N	\N	2026-03-21 18:49:35.15+00	2026-03-21 18:49:35.21+00
21	721019e8-c15d-4506-802d-b0cd20a49309	82a543e316c8440e9e0aa5022ff1662a.jpg	FAILURE	\N	\N	2026-03-21 18:52:02.01+00	2026-03-21 18:53:27.47+00
19	87a0f698-2923-40c1-913b-d148806c1cae	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	FAILURE	\N	\N	2026-03-21 18:54:37.8+00	2026-03-21 18:58:29.17+00
19	73b9cc56-0071-4daa-8fdc-9fc2ccdd5742	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	FAILURE	\N	\N	2026-03-21 19:05:36.23+00	2026-03-21 19:05:36.35+00
19	d1b240d3-6ba2-458a-976e-e3667eacafe1	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	FAILURE	\N	\N	2026-03-21 19:07:50.28+00	2026-03-21 19:07:50.41+00
19	6733a29b-0be4-49d1-9fa7-d9fcf09255a2	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	FAILURE	\N	\N	2026-03-21 19:10:32.27+00	2026-03-21 19:10:32.4+00
21	f88676d7-25e6-4a39-a6ee-f5d6874da2d2	82a543e316c8440e9e0aa5022ff1662a.jpg	SUCCESS	5.00	f88676d7-25e6-4a39-a6ee-f5d6874da2d2.jpg	2026-03-22 06:41:13.81+00	2026-03-22 06:43:56.43+00
21	81656ab9-b97a-41ab-8dae-5c2c2ce271d5	82a543e316c8440e9e0aa5022ff1662a.jpg	SUCCESS	5.00	81656ab9-b97a-41ab-8dae-5c2c2ce271d5.jpg	2026-03-22 06:43:46.85+00	2026-03-22 06:44:12.06+00
19	535c3def-5e32-4a3e-93ac-ddfc60b87334	AgACAgIAAxkBAAMsab7mH77LhHfQTjkuiNAm-snMOzEAAt4Xaxtn9flJSGlrF9nmE4wBAAMCAAN5AAM6BA.jpg	SUCCESS	5.00	535c3def-5e32-4a3e-93ac-ddfc60b87334.jpg	2026-03-22 06:47:17.36+00	2026-03-22 06:47:32.57+00
19	0f850c21-2a4e-4b03-a4a8-d6e0bc2cb06a	AgACAgIAAxkBAANZacI7GlBWYrVKiwuxyJL1JGu2f2sAAtgVaxuksBFK46TGH2GCW8oBAAMCAAN5AAM6BA.jpg	FAILURE	\N	\N	2026-03-24 07:19:55.19+00	2026-03-24 07:20:43.17+00
19	363d4501-27f5-4494-b055-73cfb6611553	AgACAgIAAxkBAANaacI8R3FQ9hZUQDAptpZspTh9NtoAAuAVaxuksBFKAAEG0-1gjfxmAQADAgADeQADOgQ.jpg	SUCCESS	5.00	363d4501-27f5-4494-b055-73cfb6611553.jpg	2026-03-24 07:24:55.96+00	2026-03-24 07:25:11.38+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, root, login, directory, password, created, tg_uuid, token_balance) FROM stdin;
23	admin	admin2	admin2_folder	n7Qp3Xk9T2mL5vR8	2026-03-16 07:13:46.53+00	\N	100
21	admin	admin	admin_folder	n7Qp3Xk9T2mL5vR8	2026-03-16 07:08:50.28+00	1114223832	100
19	admin	Vasya	Romashka	money	2026-03-14 14:11:34.14+00	\N	80
\.


--
-- Name: queries_query_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.queries_query_id_seq', 22, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 63, true);


--
-- Name: queries queries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_pkey PRIMARY KEY (query_id);


--
-- Name: sessions sessions_token_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_token_unique UNIQUE (token);


--
-- Name: tasks tasks_task_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_task_id_unique UNIQUE (task_id);


--
-- Name: users unique_dir; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_dir UNIQUE (directory);


--
-- Name: users unique_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_id PRIMARY KEY (id);


--
-- Name: users unique_login; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_login UNIQUE (login);


--
-- Name: queries unique_photo_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT unique_photo_name UNIQUE (photo_name);


--
-- Name: entry_log id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entry_log
    ADD CONSTRAINT id_fk FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- Name: queries id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT id_fk FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: sessions sessions_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_id_fk FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: tasks tasks_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_id_fk FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict WCkxNM1kJ8UegUXoCRaFsKPB5fCB0U2g62gGOldvKQnnCkKwuHJBP5pUPTgEcmh


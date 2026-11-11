# Changelog

All notable changes to Triage. The release pages (GitLab, GitHub) show the curated notes of
[GITHUB_RELEASES.md](GITHUB_RELEASES.md); this file is generated from the commits by `npm run release`.

## [0.6.0](https://github.com/sharkhunterr/triage/compare/v0.5.0...v0.6.0) (2026-11-11)


### Features

* **activity:** stop work from the Activity page — what waits, by group, each with Stop; the running analysis or check is interrupted and rolled back; Stop all; moves and emails always go through ([6740ecf](https://github.com/sharkhunterr/triage/commit/6740ecfa80bd0ea0d4b16bece78265350512622b))

## [0.5.0](https://github.com/sharkhunterr/triage/compare/v0.4.1...v0.5.0) (2026-11-11)


### Features

* **check:** a Check tab — check any library for movies that belong in another, and settle them like the review queue ([8ba2612](https://github.com/sharkhunterr/triage/commit/8ba2612795f3b0c36125cbacf30f44552a275ecf))
* **check:** a waiting movie's card — the title on the whole width, the way and the ring under it, a rule, the slider across, then its status beside the confirm button ([0e332d8](https://github.com/sharkhunterr/triage/commit/0e332d85bef05f410204a018a44c34d5ceadf228))
* **check:** choose a check's library on a slider — one stop per library, a pin where the movie is, the way to the one chosen in their colours, its confidence on the thumb, then confirm ([330b0b0](https://github.com/sharkhunterr/triage/commit/330b0b075ebe6a00f498da93a16bcdae91906ad4))
* **check:** compact choices on the check's rows — slim category chips with their confidence, an icon to leave it ([4184d92](https://github.com/sharkhunterr/triage/commit/4184d92bf71f362b6df721f67d044befcc43bd9d))
* **check:** the check's movies as timeline rows, the choices under each ([3fb4634](https://github.com/sharkhunterr/triage/commit/3fb4634833d4b88d5e9bf0aac0a5e23d74d57cac))
* **check:** the slider's thumb points the way and a light runs along it; a ruled-out library says so over its stop ([897abfe](https://github.com/sharkhunterr/triage/commit/897abfec3781b0348f2a9f731fa74c4742436e2d))
* **check:** the slider's way is an arrow, and every library shows its confidence over its stop — the chosen one in a badge kept inside the card ([aeb64d8](https://github.com/sharkhunterr/triage/commit/aeb64d8096555ad7724b9ddef399dd192a564887))
* **decision:** the sheet chooses or corrects on the library slider too — undo stays its own button; fix the slider's names with two libraries ([f728c2c](https://github.com/sharkhunterr/triage/commit/f728c2cea4db714915323b79f408394e0ab7b4a7))
* **decision:** the sheet's why drops the sentence the score chips already tell, and the TMDB box links to the movie on TMDB ([644e414](https://github.com/sharkhunterr/triage/commit/644e4147e22c694ed3958430e2c27e3b5701585f))
* **decision:** the stills drop their TMDB link, the metadata box already has it ([2a3814b](https://github.com/sharkhunterr/triage/commit/2a3814b428ae74f63d664606253897f6a1d1d417))
* **history:** a timeline per day — status on the poster, confidence as a ring in the category's colour, the day's libraries as a strip ([741d414](https://github.com/sharkhunterr/triage/commit/741d4146e554764f1ecf40cdb0f9d4fe832d8d7a))
* **locks:** a movie sorted by hand is locked in its library; checks respect locks or ignore them; modern History (#18 #19 #20) ([5e96cb0](https://github.com/sharkhunterr/triage/commit/5e96cb059b41d041c7c15ebe80234e47bf942752))
* **review:** the review queue shows its movies as the check does — the timeline card with the library slider and its confirm button ([bd31d14](https://github.com/sharkhunterr/triage/commit/bd31d14868e2b3076d387519d0b08a2ef2678284))


### Bug Fixes

* **check:** a badge on the Check tab for its gaps and doubts; Animation rules out Shows and Concerts ([2c4d0c2](https://github.com/sharkhunterr/triage/commit/2c4d0c2f011b04c2958d9fba4ae9a94b130e4958))
* **check:** a movie whose best choice is the library it is in is in place, sure or not ([89555a0](https://github.com/sharkhunterr/triage/commit/89555a0a3d6db56363852bb7b1f09868be4d8fd0))
* **check:** the check's progress bar in the theme's colours, not the device's native green ([367225d](https://github.com/sharkhunterr/triage/commit/367225d8f81e8b6b6b81ab8032e1bf81dba8e18a))
* **check:** the slider's library names keep to their own column — as wide as the gap between two stops, on two lines when long, never over their neighbour ([b256926](https://github.com/sharkhunterr/triage/commit/b2569263df2ebe5a69e8f78b2e097c7cfb4623ff))
* **locks:** a discreet padlock — by the title on the sheet, its details and Unlock in a popover; an icon with a tooltip in the lists ([3392d07](https://github.com/sharkhunterr/triage/commit/3392d0785857c3c954a9253fed3f6e015d07b69d))
* **presets:** a live-action/animated film is no cartoon — Wikidata « live-action » rules Animation out and counts for Films ([0e91332](https://github.com/sharkhunterr/triage/commit/0e91332e2394b1e872ee3ce92982679fbc19ebef))

### [0.4.1](https://github.com/sharkhunterr/triage/compare/v0.4.0...v0.4.1) (2026-11-10)


### Bug Fixes

* **email:** the review email shows each choice like the review page, and the SMTP test no longer times out on a stalled address ([336010e](https://github.com/sharkhunterr/triage/commit/336010e11cb9328daa1142fa15d0b1d2f9abe713))
* **settings:** the email test works on the server's loop and every test shows it is running or why it failed ([0de0984](https://github.com/sharkhunterr/triage/commit/0de0984dec4b0f59f1004dca0fdfd5a876ba59cd))

## [0.4.0](https://github.com/sharkhunterr/triage/compare/v0.3.2...v0.4.0) (2026-11-10)


### Features

* **categories:** Shows and Concerts presets, offered beside existing categories ([30746da](https://github.com/sharkhunterr/triage/commit/30746dad1e4d709d5ab42e75b7ef7e3f717cc57d))
* **dashboard:** 30-day chart by who sorted, by category, or analysed — sure or in doubt ([bbeb215](https://github.com/sharkhunterr/triage/commit/bbeb215cdb7a3ca622fd167201daf06d38ff51e6))
* **folders:** refresh Radarr's root folders from Settings and the category editor ([794bf11](https://github.com/sharkhunterr/triage/commit/794bf1154e6ba5d5fe13b68f234102b47f6ce9fb))
* **sheet:** metadata grouped by source — Radarr and TMDB, Wikidata and Wikipedia; presets know television specials and rockumentaries ([4d7078c](https://github.com/sharkhunterr/triage/commit/4d7078c5e4f50470f8d6e047cb793eefafb12b69))
* **sheet:** the Wikipedia opening as plain text above the Wikidata type, like TMDB's synopsis ([003166e](https://github.com/sharkhunterr/triage/commit/003166e51355cf0fb968609226cbcf1f711d3cbf))
* **sheet:** who asked for the movie in Seerr and when, else when Radarr added it ([14245cc](https://github.com/sharkhunterr/triage/commit/14245cc6032fb5e617deb885354f0f67dbbff365))
* **wiki:** Wikidata type as a rule field, Wikipedia opening for the AI and on the sheet ([a1fea1f](https://github.com/sharkhunterr/triage/commit/a1fea1f566ab8386bd3fa3fe73c2a28d8c09520f))


### Bug Fixes

* **classify:** the AI is a real second opinion — no fallback default over it, richer Shows/Concerts rules, complete a preset ([c5adbd6](https://github.com/sharkhunterr/triage/commit/c5adbd614955ba4f757f7748676b71c3d2bae375))

### [0.3.2](https://github.com/sharkhunterr/triage/compare/v0.3.1...v0.3.2) (2026-11-09)

### [0.3.1](https://github.com/sharkhunterr/triage/compare/v0.3.0...v0.3.1) (2026-11-09)

## [0.3.0](https://github.com/sharkhunterr/triage/compare/v0.2.0...v0.3.0) (2026-11-09)


### Features

* **dashboard:** a more modern dashboard — what waits first, the week's trend, the month, the libraries, the services ([a6d7717](https://github.com/sharkhunterr/triage/commit/a6d7717abd64e712a1752e03b0da7cc6883d0086))
* **review:** pages and a number of movies per page; a movie's sheet goes back where it was opened from ([f054f03](https://github.com/sharkhunterr/triage/commit/f054f0338c510f24cb254108cf4a86305cea56c4))


### Bug Fixes

* **seerr:** ask Overseerr only what it knows, so verifying a request no longer fails with HTTP 400 ([595c7e8](https://github.com/sharkhunterr/triage/commit/595c7e821ed939cc32ccdee87204f65feeac1ed7))

## [0.2.0](https://github.com/sharkhunterr/triage/compare/v0.1.0...v0.2.0) (2026-11-09)


### Features

* **sheet:** TMDB stills to check the movie match ([deebfa0](https://github.com/sharkhunterr/triage/commit/deebfa06fff7f46d46146f37baacb8db320dc798))

## 0.1.0 (2026-11-08)


### Features

* **activity:** analyses asked from the movie page show in Activity ([86e1ee0](https://github.com/sharkhunterr/triage/commit/86e1ee0031feb3e439fb793ba2880decac9801a2))
* **activity:** live progress of every analysis, step by step ([d8726dd](https://github.com/sharkhunterr/triage/commit/d8726dda6cea3c1cd6f545928a4aa688258d86d7))
* adult content stays out of Animation; undone moves shown as such ([9191f1f](https://github.com/sharkhunterr/triage/commit/9191f1f131b6782aa10072363e7d1898cc7cc1e4))
* **ai:** the AI reads each category's folder and rules, and what they found ([140c524](https://github.com/sharkhunterr/triage/commit/140c524cc9747c49513a9820015cecf62f4be253))
* **categories:** categories and rules, movies/animation preset, editor (US3, T039–T044) ([9cffa66](https://github.com/sharkhunterr/triage/commit/9cffa66c2b079c161471f6739f65ea7e0146e3f1))
* **decision:** Analyze now, at the top of the movie page ([7fca111](https://github.com/sharkhunterr/triage/commit/7fca1112892421cd765eadeb379abb33ee578df7))
* **decision:** category colors and every keyword shown ([f0df457](https://github.com/sharkhunterr/triage/commit/f0df457559603ff7d289ed3b73867be586b8022f))
* Docker image (PUID/PGID), GitLab CI, README with screenshots, release notes; hide superseded decisions by default (T092–T098) ([b5e8daa](https://github.com/sharkhunterr/triage/commit/b5e8daaa183e13fb349a0f3907bf85961bfe8792))
* exclusion rules, AI second opinion, clearer movie page ([44dbea2](https://github.com/sharkhunterr/triage/commit/44dbea2f592fef3224b719fc6cd4dff5ace87d20))
* foundations — models and migration, settings, auth, adapters with fakes, scoring engine, decision states, work queue, frontend shell (T007–T037) ([bd54ed7](https://github.com/sharkhunterr/triage/commit/bd54ed72c5174391e7701f527608cab58f656d32))
* **history:** undo a move, or every move of a period ([83b0de6](https://github.com/sharkhunterr/triage/commit/83b0de6a922942516151582ca3f66c2f7ef2acdb))
* **nav:** Activity in the phone bottom bar ([a9b5a1b](https://github.com/sharkhunterr/triage/commit/a9b5a1b10b9fc0fdb2497f9d48e429ce0b379e27))
* **preset:** '3d animation' keyword counts for Animation ([be97068](https://github.com/sharkhunterr/triage/commit/be97068bfc9281214ff78039035b64223b250f19))
* **preset:** live action remakes go to Movies (decisive keyword) ([73cede5](https://github.com/sharkhunterr/triage/commit/73cede5295e62b62d679456535499b6935131f39))
* **preview:** preview mode, apply/dismiss/apply-confident, simulate; settings API and page with mode switch (US4 T064–T068, US8 T083/T085) ([ed787de](https://github.com/sharkhunterr/triage/commit/ed787dee7dcc428791843a4575fb11afa7beed5e))
* request verification, corrections and history, status page, Seerr webhook (US6, US7, US8, US9) ([115bc0d](https://github.com/sharkhunterr/triage/commit/115bc0d5f398f0019abbd7c7f63abc6c995effb1))
* **review:** Analyze… everything, waiting, or new only ([a4258a5](https://github.com/sharkhunterr/triage/commit/a4258a548805bf456bcf9012e5b2dae55c19758a))
* **review:** decide all, analyze all again, colored choices; phone fixes ([58f77f3](https://github.com/sharkhunterr/triage/commit/58f77f3c6b2fedd59b90931cf1236ed00dd2a8f6))
* **review:** hold doubtful movies, one email per run with single-use links, review queue (US2, T057–T062) ([246308b](https://github.com/sharkhunterr/triage/commit/246308bb1de7e795a7a2b05fe81e768b992ff2d6))
* **scans:** scan any root folder into proposals, with progress, cancel and scoped apply (US5, T070–T073) ([933af68](https://github.com/sharkhunterr/triage/commit/933af68179fbb908a126f45edf84b9a4c9248b4b))
* **setup:** guided setup wizard with a test for every service ([5042c1b](https://github.com/sharkhunterr/triage/commit/5042c1bb4970d5b8091786ad5391024202cddfd6))
* **sorting:** poll intake folders, classify with rules then AI, move through Radarr's editor; dashboard and decision detail (US1, T046–T055) ([bc01823](https://github.com/sharkhunterr/triage/commit/bc018235b6fbfa10fbbc7ad288a333e066eaa30a))
* titles in the TMDB language, confidence on every choice, AI points shown ([be84fcf](https://github.com/sharkhunterr/triage/commit/be84fcfa464e25ae28c660dba2d99271b1e4fde4))
* **tmdb:** language and country setting ([9228ce1](https://github.com/sharkhunterr/triage/commit/9228ce16d08e2c249c726aa3cc23bee86109b8f7))


### Bug Fixes

* an undone move waits for the owner again; Analyze all again takes it ([0e5f1b3](https://github.com/sharkhunterr/triage/commit/0e5f1b333ccf6a5a29732c694a75c26ad5f742c7))
* **categories:** stable keys for rule rows in the editor ([9d16eec](https://github.com/sharkhunterr/triage/commit/9d16eec8d308b0876b9a983178bc775e74d23bda))
* **dashboard:** undone moves are not counted as sorted ([7147d0b](https://github.com/sharkhunterr/triage/commit/7147d0b2c071755d8bf4741841cbd1a51a8e5744))
* owner actions go first in the queue; French titles never taken from Quebec ([3cbc063](https://github.com/sharkhunterr/triage/commit/3cbc0638723ee2b84246d8a77d7740c96a355c26))
* **webhook:** check again shortly after a Seerr notification ([cd0a877](https://github.com/sharkhunterr/triage/commit/cd0a877909c5703e30e5d76481a635dba080aa86))
* **worker:** never hold the database lock while waiting on TMDB or the AI ([9994753](https://github.com/sharkhunterr/triage/commit/99947530d66aad9c6212b5a1b008da8c7a3de187))

# Changelog

All notable changes to Triage. The release pages (GitLab, GitHub) show the curated notes of
[GITHUB_RELEASES.md](GITHUB_RELEASES.md); this file is generated from the commits by `npm run release`.

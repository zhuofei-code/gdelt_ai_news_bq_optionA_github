# Option A Source Selection Record

Selection date: 2026-03-11

Scope: 11 countries, fixed window 2018-06-01 to 2025-06-01, target design `5 mainstream + 5 specialist` per country.

Status: provisional. This file records the current candidate set before SQL host profiling. The specialist choices were made with editorial-fit heuristics and light web verification. They still need continuity and field-concentration screening before any production run.

## Selection rules used

- Mainstream outlets follow the March 2026 domain screening report baseline.
- Specialist slots are one per field: `business_finance`, `technology_digital`, `health_biomedicine`, `energy_climate_industry`, `law_policy_regulation`.
- Preference order: local specialist news site, then national trade/professional publication, then regional fallback if the local specialist market is too thin.
- Some small-market legal or energy candidates are information services, trade associations, or publisher-led legal current-affairs portals rather than classic general-interest newsrooms. These were retained only as pre-profiling candidates.

## Profiling thresholds to apply next

- `active_months >= 70 / 84`
- `median_monthly_records >= 30`
- `field_concentration_share >= 0.35`
- `maximum_single_month_share <= 0.35`
- `duplicate_content_ratio <= 0.25`

## Country Selections

### IS

Mainstream: `ruv.is`, `mbl.is`, `visir.is`, `dv.is`, `stundin.is`

Specialist:

- `business_finance`: `vb.is`
- `technology_digital`: `startupiceland.com`
- `health_biomedicine`: `laeknabladid.is`
- `energy_climate_industry`: `samorka.is`
- `law_policy_regulation`: `kjarninn.is`

Risk note: Iceland is the hardest market in this sample for true specialist-domain coverage. The technology, energy, and policy picks are the highest-priority domains to validate in profiling.

### FI

Mainstream: `yle.fi`, `hs.fi`, `iltasanomat.fi`, `mtvuutiset.fi`, `is.fi`

Specialist:

- `business_finance`: `kauppalehti.fi`
- `technology_digital`: `tivi.fi`
- `health_biomedicine`: `mediuutiset.fi`
- `energy_climate_industry`: `energiauutiset.fi`
- `law_policy_regulation`: `edilex.fi`

Risk note: `edilex.fi` is a legal-information platform and should be validated for article-style continuity rather than assumed.

### BE

Mainstream: `hln.be`, `lesoir.be`, `vrt.be`, `nieuwsblad.be`, `lalibre.be`

Specialist:

- `business_finance`: `lecho.be`
- `technology_digital`: `datanews.knack.be`
- `health_biomedicine`: `medi-sphere.be`
- `energy_climate_industry`: `energynews.pro`
- `law_policy_regulation`: `legalnews.be`

Risk note: `energynews.pro` is a regional energy outlet, not a Belgium-only newsroom. It should be kept only if the profiling stage shows meaningful Belgium-facing continuity.

### FR

Mainstream: `lemonde.fr`, `lefigaro.fr`, `franceinfo.fr`, `liberation.fr`, `ouest-france.fr`

Specialist:

- `business_finance`: `lesechos.fr`
- `technology_digital`: `numerama.com`
- `health_biomedicine`: `lequotidiendumedecin.fr`
- `energy_climate_industry`: `actu-environnement.com`
- `law_policy_regulation`: `dalloz-actualite.fr`

### PT

Mainstream: `rtp.pt`, `publico.pt`, `observador.pt`, `sicnoticias.pt`, `jornaldenegocios.pt`

Specialist:

- `business_finance`: `eco.sapo.pt`
- `technology_digital`: `tek.sapo.pt`
- `health_biomedicine`: `newsfarma.pt`
- `energy_climate_industry`: `ambienteonline.pt`
- `law_policy_regulation`: `iberianlawyer.com`

Risk note: `iberianlawyer.com` is Iberian rather than Portugal-only. Retain only if profiling shows a usable Portugal-facing legal-business signal.

### AT

Mainstream: `orf.at`, `derstandard.at`, `krone.at`, `kurier.at`, `diepresse.com`

Specialist:

- `business_finance`: `trend.at`
- `technology_digital`: `futurezone.at`
- `health_biomedicine`: `aerztezeitung.at`
- `energy_climate_industry`: `industriemagazin.at`
- `law_policy_regulation`: `manz.at`

Risk note: `manz.at` is an established legal publisher with current-affairs content, but it still needs host-level continuity checks.

### CZ

Mainstream: `blesk.cz`, `aktualne.cz`, `ceskatelevize.cz`, `irozhlas.cz`, `denik.cz`

Specialist:

- `business_finance`: `e15.cz`
- `technology_digital`: `lupa.cz`
- `health_biomedicine`: `zdravezpravy.cz`
- `energy_climate_industry`: `oenergetice.cz`
- `law_policy_regulation`: `pravniprostor.cz`

### PL

Mainstream: `tvn24.pl`, `onet.pl`, `gazeta.pl`, `rp.pl`, `wyborcza.pl`

Specialist:

- `business_finance`: `pb.pl`
- `technology_digital`: `spidersweb.pl`
- `health_biomedicine`: `rynekzdrowia.pl`
- `energy_climate_industry`: `wysokienapiecie.pl`
- `law_policy_regulation`: `prawo.pl`

### HU

Mainstream: `telex.hu`, `24.hu`, `hvg.hu`, `index.hu`, `portfolio.hu`

Specialist:

- `business_finance`: `vg.hu`
- `technology_digital`: `hwsw.hu`
- `health_biomedicine`: `medicalonline.hu`
- `energy_climate_industry`: `energiaoldal.hu`
- `law_policy_regulation`: `jogiforum.hu`

### SI

Mainstream: `24ur.com`, `rtvslo.si`, `delo.si`, `dnevnik.si`, `vecer.com`

Specialist:

- `business_finance`: `finance.si`
- `technology_digital`: `monitor.si`
- `health_biomedicine`: `medicina-danes.si`
- `energy_climate_industry`: `energetika.net`
- `law_policy_regulation`: `iusinfo.si`

Risk note: `iusinfo.si` is closer to a legal information portal than a classic newsroom. It needs explicit validation before production use.

### UK

Mainstream: `bbc.co.uk`, `theguardian.com`, `telegraph.co.uk`, `independent.co.uk`, `dailymail.co.uk`

Specialist:

- `business_finance`: `ft.com`
- `technology_digital`: `theregister.com`
- `health_biomedicine`: `hsj.co.uk`
- `energy_climate_industry`: `businessgreen.com`
- `law_policy_regulation`: `lawgazette.co.uk`

## Immediate next step

Run host profiling on the specialist set first and score each candidate on continuity, volume, and field concentration. The first domains to stress-test should be:

- Iceland: `startupiceland.com`, `samorka.is`, `kjarninn.is`
- Belgium: `energynews.pro`
- Portugal: `iberianlawyer.com`
- Austria: `manz.at`
- Slovenia: `iusinfo.si`

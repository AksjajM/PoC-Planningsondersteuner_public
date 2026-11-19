# Planningsondersteuner (afstudeer-PoC)

Webapplicatie die planningsinformatie van een supportafdeling op één plek vastlegt: beschikbaarheid per dagdeel, rollen, verlof en minimale bezetting, met automatische conflictsignalering in een weekoverzicht.

*Afstudeerproject HBO-ICT Software Engineering, uitgevoerd bij een softwarebedrijf. Alleen niet-vertrouwelijke onderdelen staan hier.*

## Probleem
Planningsinformatie stond verspreid over meerdere tools en afspraken. Dat kostte handmatige controletijd en maakte het proces persoonsafhankelijk.

## Oplossing
- Eén database als Single Source of Truth
- Validatieregels in een aparte servicelaag (geen logica in templates)
- Weekoverzicht met rood/groen-indicator per rol
- Verlofaanvragen met goedkeuren en afwijzen, CSV-export

## Techniek
Python · Django · SQLite (PoC; PostgreSQL als advies) · Docker · GitLab CI/CD · Pylint · pytest/Django-tests

## Kwaliteit en validatie
- 178 geautomatiseerde tests, Pylint 10.00/10
- Gebruikerstest: 75 testcases, 3 testers; uitkomsten vergeleken met triangulatie
- 9 niet-functionele eisen (ISO/IEC 25010): 6 behaald, 1 grotendeels, 2 niet volledig
- Architectuurkeuzes vastgelegd als ADR's (o.a. Django, SQLite met PostgreSQL-advies, C4-model)

## De beperkingen
Twee gebreken zijn gevonden en benoemd (een uitzondering is niet op elk scherm zichtbaar; de export mist uitzonderingen). Tijdwinst is niet aangetoond. De PoC is geslaagd als concept, niet als productieklare oplossing.
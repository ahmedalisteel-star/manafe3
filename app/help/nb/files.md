---
title: Åpne, lagre og eksportere filer
summary: Manafe3-modellfilen, hver eksport den skriver, hvor filene havner, og hva som er forskjellig etter nettleser og forbindelse.
keywords: åpne, lagre, eksporter, last ned, fil, json, ifc, nc1, dstv, csv, pdf, zip, formater, importer
from: bd715ea3
---

Manafe3 har én egen fil, modellen, og fem eksporter. Hver lagring og hver eksport er en nedlasting. Ingenting lastes opp, og ingenting beholdes på en server.

## Modellfilen

En Manafe3-modell lagres som `<navn>.detailcraft.json`, der `<navn>` er modellnavnet i panelet {{ui:Modell}}. Den inneholder rutenettene, nivåene, stavene (med hull og utklinkninger), forbindelsene og innstillingene deres, fundamentene og dine egendefinerte profiler.

Deler, numre, bolter, sveiser og stenger lagres ikke: Manafe3 regner dem ut på nytt fra modellen hver gang den åpnes. Derfor er en modellfil liten.

### Lagre

1. Skriv et navn i feltet {{ui:Navn}} øverst i panelet {{ui:Modell}}.
2. Velg {{ui:Lagre}} i gruppen {{ui:Fil}}, eller trykk {{key:Mod+S}}.
3. Nettleseren laster ned `<navn>.detailcraft.json`. Statuslinjen sier «Lagret … (lastet ned)», og prikken i begynnelsen av nettleserfanens tittel forsvinner.

Hver lagring er en ny nedlasting. Nettleseren skriver ikke over filen du åpnet; avhengig av innstillingene legger den et tall til navnet, for eksempel `Frame (1).detailcraft.json`, eller spør hvor den skal lagres. Behold dine egne versjoner ved å gi nedlastingene nytt navn.

:::chromium
Chrome og Edge lagrer i mappen Nedlastinger med mindre **Spør hvor hver fil skal lagres før nedlasting** er på i nettleserens nedlastingsinnstillinger. Slå det på hvis du vil velge mappe og filnavn hver gang.
:::

:::firefox
Firefox lagrer i mappen Nedlastinger, eller spør hver gang hvis **Spør alltid hvor filer skal lagres** er på i innstillingene.
:::

:::safari
Safari lagrer i mappen Nedlastinger. For å endre mappen åpner du **Safari, Innstillinger, Generelt, Plassering for filnedlasting**.
:::

### Åpne

1. Velg {{ui:Åpne}} i gruppen {{ui:Fil}}, eller trykk {{key:Mod+O}}.
2. Velg en `.detailcraft.json`-fil.

Eller dra filen fra {{pick:mac=Finder|windows=Filutforsker|linux=filbehandleren}} og slipp den på visningen. Visningen sier «Slipp en Manafe3-modell for å åpne den» mens du drar.

Hvis den åpne modellen har ulagrede endringer, spør Manafe3 først: {{ui:Avbryt}}, {{ui:Forkast endringer}} eller {{ui:Lagre først}}.

Manafe3 kontrollerer hvert felt i en fil før den bruker den. Alt den ikke kan bruke, utelates, og statuslinjen sier hva, for eksempel «2 staver var ugyldige og er utelatt.» En modell lagret av en nyere Manafe3 avvises med en melding i stedet for å åpnes halvveis riktig.

### Dette åpner den

Sine egne modellfiler (`.json`, opptil 50 MB) og IFC-filer (`.ifc`, IFC2X3 eller IFC4, opptil 200 MB). En IFC-fil, åpnet eller hentet inn med {{ui:Importer IFC}}, blir en ny modell av bjelkene, søylene, stavene, platene, rutenettene og nivåene sine, med hullene og utklinkningene kuttet i dem og boltene som løse bolter; en rapport lister det som ble utelatt. Se [IFC-eksport](topic:ifc-export#import). Den åpner ikke DWG, DXF eller noe annet detaljeringsprograms modell ennå; et forsøk viser «Manafe3 åpner sine egne modeller (.detailcraft.json) og IFC-filer (.ifc).»

## Tapt arbeid, nylige filer, skrivebordsappen

- Mens modellen har endringer du ikke har lagret, beholder Manafe3 en kopi i denne nettleseren. Hvis fanen eller nettleseren stopper før du lagrer, spør den **Gjenopprette arbeidet ditt?** neste gang du åpner Manafe3: gjenopprett kopien, eller la den gå. Se [Gjenopprett arbeidet ditt](common:recover).
- Modeller du nylig åpnet, listes på startskjermen når nettleseren lar Manafe3 åpne dem igjen; klikk én for å åpne den på nytt.
- I skrivebordsappen skriver {{ui:Lagre}} modellen tilbake til filen du åpnet (i nettleseren laster den ned en kopi), og et dobbeltklikk på en Manafe3-modell eller en IFC-fil åpner den i Manafe3.

## Eksporter

Alle eksporter bruker modellnavnet. Velg dem i gruppen {{ui:Utdata}}.

| Knapp | Fil | Hva som er i den |
|---|---|---|
| {{ui:IFC}} | `<navn>.ifc` | IFC4: etasjer, rutenett, hver ståldel som en profilekstrudering med hull og utklinkninger, sammenstillinger, bolter og ankerstenger, fundamenter og hver stang. Se [Eksporter IFC](topic:ifc-export). |
| {{ui:NC-filer}} | `<navn> NC.zip` | Én DSTV-`.nc1`-fil per delenummer. Se [Send NC-filer til verkstedet](topic:nc-export). |
| {{ui:BOM}} | `<navn> BOM.csv` | Tre tabeller i én fil: deler, sammenstillinger, og bolter og ankerstenger. Se [Numre og stykklisten](topic:marks-and-bom). |
| {{ui:Bøying}} | `<navn> bending schedule.csv` | Hvert stangnummer i fundamentene. Se [Fundamenter og armering](topic:footings-and-rebar). |
| {{ui:Verkstedtegning}} | `<navn> <nummer>.pdf` | Ett ark (A3 hvis du ikke valgte en annen størrelse) for den valgte delen (I-profiler og plater). Se [Lag en verkstedtegning](topic:shop-drawings). |
| {{ui:Tegninger}} | `<navn> drawings.pdf`, `<navn> <ark>.pdf`; `<navn> <ark>.dwg` eller `.dxf`, flere i `<navn> drawings DWG.zip` (eller `DXF.zip`) | Planene, fasadene og sammenstillingstegningene på arkstørrelsen du valgte; DWG og DXF i full størrelse, 1 enhet = 1 mm på papiret. Se [Hovedplaner og sammenstillingstegninger](topic:drawings). |

### Merknader om CSV-filene

- De begynner med et byterekkefølgemerke slik at regnearkprogrammer leser tegn med aksent riktig.
- En celle som begynner med `=`, `+`, `-` eller `@` (og ikke er et vanlig tall) får en innledende apostrof, slik at et regneark aldri kjører den som en formel.
- Lengder er millimeter og vekter kilogram.

### Merknader om PDF-en

Teksten i PDF-en bruker standardfonten Helvetica. Tegn den ikke har (utenfor det vesteuropeiske settet) skrives ut som «?», og statuslinjen sier hvor mange.

## Enheter

Manafe3 arbeider i millimeter overalt: rutenett, nivåer, koordinater, profiler, hull og hver eksport. Profilnavn beholder sin publiserte form (W12x50 er en amerikansk betegnelse selv om målene vises i mm). Det finnes ingen imperial inndata ennå.

## Tilkoblet og frakoblet

Å åpne, lagre og eksportere skjer alt i nettleseren din, så det fungerer likt med eller uten forbindelse når Manafe3 er lastet.

For å bruke Manafe3 uten forbindelse senere velger du {{ui:Lagre for frakoblet bruk}} i appfeltet mens du er tilkoblet. Knappen teller opp («Lagrer 3 av 20») og sier deretter {{ui:Klar frakoblet}}. Den lagrede kopien inneholder 3D-grafikkbiblioteket (omtrent 2,6 MB) og denne hjelpen, så når den er lagret, fungerer 3D-visningen, hver eksport og hjelpen frakoblet. Detaljer, og hva som fortsatt trenger forbindelse: [Arbeide frakoblet](common:offline).

:::offline
Du er frakoblet. Hvis appfeltet viser {{ui:Klar frakoblet}}, fungerer åpning, lagring og eksport som vanlig. Hvis ikke, hold denne fanen åpen, ikke last den på nytt før du er tilkoblet igjen, og lagre modellen din nå.
:::

Skylagring finnes ikke ennå, og det finnes ingen skrivebordsversjoner ennå. Ta sikkerhetskopi av `.detailcraft.json`-filene dine slik du gjør med andre arbeidsfiler. Mer i [Hvor filene dine havner](common:your-files).

## Ulagret arbeid

Manafe3 beholder modellen bare i den åpne fanen. Hvis du lukker eller laster fanen på nytt med ulagrede endringer, spør nettleseren om du vil forlate siden; ordlyden er nettleserens egen. Lagre ofte med {{key:Mod+S}}.

---
title: Manafe3 gebruiken met een AI-assistent
summary: Laat uw eigen AI-assistent of script het model, de onderdelen, problemen en clashes lezen, verbindingen en onderdelen toevoegen, opslaan en exporteren (ook USD): rechten, verbinden via Manafe3 Desktop en het activiteitenlogboek.
keywords: ai, assistent, agent, mcp, model context protocol, script, automatisering, onderdelen, clashes, verbindingen, rechten, verbreken, activiteit, ongedaan maken
from: d624c9a0
---

## Wat u gaat leren

Hoe u een AI-assistent (of een script dat u zelf hebt geschreven) met Manafe3 laat werken, en hoe u beslist wat die mag aanraken.

Manafe3 heeft **geen eigen AI** en stuurt niets ergens naartoe. U brengt de assistent mee: elk programma dat het Model Context Protocol (MCP) spreekt. Manafe3 geeft die alleen hulpmiddelen, en u kiest welke.

## Inschakelen

1. Open {{ui:Instellingen}} (het tandwiel in de appbalk, of {{key:Mod+,}}) en ga naar het tabblad {{ui:Manafe3}}.
2. Vink onder {{ui:Assistenten}} **AI-assistenten en scripts Manafe3 laten gebruiken** aan. Het staat uit totdat u dat doet.
3. Kies wat het mag doen: **Lezen** is vanaf het begin aangevinkt; vink **Bewerken**, **Opslaan** of **Exporteren** alleen aan wanneer u ze nodig heeft.

Hulpmiddelen buiten de rechten die u hebt aangevinkt, worden niet aan de assistent aangeboden, en als hij er toch om vraagt, weigert Manafe3 dat en schrijft het dit in het activiteitenlogboek. Het uitzetten van de schakelaar beëindigt alle verbindingen tegelijk.

## Uw assistent verbinden

Assistenten verbinden via **Manafe3 Desktop** op uw computer: Studio draait een kleine server die alleen deze computer kan bereiken, beschermd door een token dat het bij elke start maakt. Kies in Studio {{ui:Een assistent verbinden}} en kopieer het adres en het token naar uw assistent (Studio toont de exacte instellingen om te plakken). Deel het token nooit.

:::note
Een browsertab kan geen verbinding voor een assistent openen: in de browserapps heeft de schakelaar geen effect totdat u Manafe3 Desktop op uw computer gebruikt.
:::

## U blijft de baas

- **Elke wijziging is één stap ongedaan maken**, met het label van de assistent (bijvoorbeeld "Assistent: ligger toevoegen", "Assistent: knoopplaten toevoegen"). {{key:Mod+Z}} neemt de laatste wijziging van de assistent in zijn geheel terug. De eigen `undo` van de assistent neemt alleen zijn eigen stappen terug, nooit de uwe, tenzij hij daar uitdrukkelijk om vraagt.
- **Het wacht op u.** Terwijl u een onderdeel plaatst, onderdelen verplaatst of plakt, weigert Manafe3 de wijzigingen van de assistent en vraagt het die het opnieuw te proberen.
- **U weet wanneer er een is verbonden.** Een knop in de appbalk noemt de assistent zolang die verbonden is; klik erop om te zien wat hij mag, of om hem te **Verbreken**.
- **Activiteit.** {{ui:Instellingen}} › {{ui:Manafe3}} › {{ui:Assistenten}} › {{ui:Activiteit}} toont elke aanroep: wanneer, welk hulpmiddel, gedaan of geweigerd. {{ui:Het logboek opslaan}} bewaart een kopie.

## Wat een assistent kan vragen

Alle lengtes zijn in millimeters, punten `[x, y, z]` met z omhoog, zoals in het model.

| Hulpmiddel | Recht | Wat het doet |
|---|---|---|
| `app_info`, `model_describe` | Lezen | Het geopende model: rasters, niveaus, fasen, onderdelen per type en profiel, verbindingen, funderingen, trappen, onderdelen, staalgewicht, problemen |
| `parts_list` | Lezen | Onderdeelmerken met profiel, materiaal, snijlengte, aantal, gewicht, fase en montagemerken; per type, profiel, merk of fase |
| `problems_list` | Lezen | Wat het tabblad {{ui:Problemen}} toont, elk met waar het over gaat |
| `clash_check` | Lezen | De [clashcontrole](topic:clash-check), met de tolerantie en fasen |
| `selection_get` | Lezen | Wat u hebt geselecteerd |
| `selection_set` | Bewerken | Selecteert onderdelen, verbindingen, funderingen of trappen (op id of onderdeelmerk) om ze aan u te tonen; wijzigt niets |
| `member_add` | Bewerken | Een ligger, kolom, verband of plaat tussen twee punten |
| `connection_add` | Bewerken | Eindplaten, schuifplaten, voetplaten, lasverbindingen of knoopplaten waar de gegeven onderdelen samenkomen, zoals de knoppen {{ui:Verbinden}} doen |
| `undo` | Bewerken | Neemt de laatste stappen van de assistent terug |
| `model_save` | Opslaan | Het eigen Opslaan van Manafe3 |
| `model_export` | Exporteren | IFC, NC-bestanden, BOM, buigstaat, KISS-bestand of snijlijst, zoals de knoppen {{ui:Uitvoer}} die maken |
| `usd_export` | Exporteren | Het staalmodel als USD (.usda, .usdc of .usdz), zoals {{ui:Uitvoer}} › {{ui:USD}} het schrijft (zie [Het staalmodel exporteren als USD](topic:usd)); in Studio kan het bestand naar een map worden geschreven die u heeft toegestaan |

## Als iets niet werkt

- **De assistent ziet geen Manafe3-hulpmiddelen:** controleer dat de schakelaar in dit venster aan staat, en dat het venster open is in Studio.
- **"heeft het bewerkingsrecht nodig"** (of opslaan, exporteren): vink het aan onder {{ui:Assistenten}}, en vraag het daarna opnieuw.
- **"U plaatst een onderdeel":** rond af wat u doet (of druk op {{key:Esc}}), en laat de assistent het daarna opnieuw proberen.
- **Fouten "401" of "token":** het token is gewijzigd (Studio is opnieuw gestart, of {{ui:Nieuw token}}). Kopieer het nieuwe in de instellingen van de assistent.

## Zie ook

- [Recepten voor AI-assistenten](common:assistants-recipes): uitgewerkte voorbeelden, elk met de hulpmiddelen die het aanroept.

---
title: Manafe3 izmantošana ar AI asistentu
summary: Ļaujiet savam AI asistentam vai skriptam lasīt modeli, tā detaļas, problēmas un sadursmes, pievienot elementus un savienojumus, saglabāt un eksportēt (arī USD): atļaujas, savienošana caur Manafe3 Desktop un aktivitātes žurnāls.
keywords: ai, asistents, aģents, mcp, model context protocol, skripts, automatizācija, detaļas, sadursmes, savienojumi, atļaujas, atvienot, aktivitāte, atsaukt
from: d624c9a0
---

## Ko jūs uzzināsiet

Kā ļaut AI asistentam (vai jūsu uzrakstītam skriptam) strādāt ar Manafe3 un kā izlemt, ko tas drīkst mainīt.

Manafe3 **pats nav AI** un nekam neko nesūta. Jūs nodrošināt asistentu: jebkuru programmu, kas runā Model Context Protocol (MCP). Manafe3 tikai dod tam rīkus, un jūs izvēlaties, kurus.

## Ieslēgt

1. Atveriet {{ui:Iestatījumi}} (zobrats lietotnes joslā vai {{key:Mod+,}}) un dodieties uz cilni {{ui:Manafe3}}.
2. Sadaļā {{ui:Asistenti}} atzīmējiet **Ļaut AI asistentiem un skriptiem izmantot Manafe3**. Sākotnēji tas ir izslēgts, līdz to ieslēdzat.
3. Izvēlieties, ko tas drīkst: **Lasīt** sākotnēji ir atzīmēts; atzīmējiet **Rediģēt**, **Saglabāt** vai **Eksportēt** tikai tad, kad tie ir vajadzīgi.

Rīki ārpus atļaujām, ko atzīmējāt, asistentam netiek piedāvāti, un, ja tas tomēr pieprasa kādu no tiem, Manafe3 to noraida un ieraksta aktivitāšu žurnālā. Izslēdzot slēdzi, uzreiz beidzas visi savienojumi.

## Savienot asistentu

Asistenti savienojas caur **Manafe3 Desktop** jūsu datorā: Studio palaiž nelielu serveri, ko var sasniegt tikai šis dators, un to aizsargā token, ko tas izveido katru reizi, kad tiek palaists. Studio sadaļā izvēlieties {{ui:Savienot asistentu}} un nokopējiet adresi un token savā asistentā (Studio parāda precīzos iestatījumus, ko ielīmēt). Nekad nedalieties ar token.

:::note
Pārlūkprogrammas cilne nevar atvērt savienojumu asistentam: pārlūkprogrammas lietotnēs slēdzim nav nekādas ietekmes, kamēr neizmantojat Manafe3 Desktop savā datorā.
:::

## Jūs paliekat atbildīgs

- **Katra izmaiņa ir viens atsaukšanas solis**, nosaukts kā asistenta (piemēram, "Asistents: pievienot siju", "Asistents: pievienot stiprinājumus"). {{key:Mod+Z}} atsauc asistenta pēdējo izmaiņu kopumā. Asistenta paša `undo` atsauc tikai tā paša soļus, nevis jūsu, ja vien tas to nepieprasa skaidri.
- **Tas gaida jūs.** Kamēr novietojat elementu, pārvietojat detaļas vai ielīmējat, Manafe3 noraida asistenta izmaiņas un liek tam mēģināt vēlreiz.
- **Jūs zināt, kad tas ir savienots.** Lietotnes joslā poga nosauc asistentu, kamēr tas ir savienots; noklikšķiniet uz tās, lai redzētu, ko tas drīkst, vai lai to **Atvienotu**.
- **Aktivitāte.** {{ui:Iestatījumi}} › {{ui:Manafe3}} › {{ui:Asistenti}} › {{ui:Aktivitāte}} uzskaita katru izsaukumu: kad, kuru rīku, izpildīts vai noraidīts. {{ui:Saglabāt žurnālu}} saglabā kopiju.

## Ko asistents var pieprasīt

Visi garumi ir milimetros, punkti `[x, y, z]` ar z uz augšu, kā modelī.

| Rīks | Atļauja | Ko tas dara |
|---|---|---|
| `app_info`, `model_describe` | Lasīt | Atvērtais modelis: režģi, līmeņi, fāzes, elementi pēc tipa un profila, savienojumi, pamati, kāpnes, detaļas, tērauda svars, problēmas |
| `parts_list` | Lasīt | Detaļu marķējumi ar profilu, materiālu, griezuma garumu, skaitu, svaru, fāzi un montāžas marķējumiem; pēc tipa, profila, marķējuma vai fāzes |
| `problems_list` | Lasīt | Ko uzskaita cilne {{ui:Problēmas}}, katrs ar to, par ko tas ir |
| `clash_check` | Lasīt | [sadursmju pārbaude](topic:clash-check), ar tās pielaidi un fāzēm |
| `selection_get` | Lasīt | Ko jūs esat atlasījis |
| `selection_set` | Rediģēt | Atlasa elementus, savienojumus, pamatus vai kāpnes (pēc id vai detaļas marķējuma), lai tos parādītu jums; neko nemaina |
| `member_add` | Rediģēt | Sija, kolonna, saite vai plātne starp diviem punktiem |
| `connection_add` | Rediģēt | Galu plātnes, bīdes cilpas, pamata plātnes, savienojumi vai stiprinājumi, kur norādītie elementi saskaras, kā to dara pogas {{ui:Savienot}} |
| `undo` | Rediģēt | Atsauc asistenta pēdējos soļus |
| `model_save` | Saglabāt | Manafe3 pašu saglabāšana |
| `model_export` | Eksportēt | IFC, NC faili, BOM, liekšanas saraksts, KISS fails vai griezumu saraksts, kā tos veido pogas {{ui:Izvade}} |
| `usd_export` | Eksportēt | Tērauda modelis kā USD (.usda, .usdc vai .usdz), kā to raksta {{ui:Izvade}} › {{ui:USD}} (skatiet [Eksportēt tērauda modeli kā USD](topic:usd)); Studio tas var uzrakstīt failu mapē, kuru esat atļāvis |

## Ja kaut kas nedarbojas

- **Asistents neredz Manafe3 rīkus:** pārbaudiet, vai slēdzis ir ieslēgts šajā logā un vai logs ir atvērts Studio.
- **"nepieciešama rediģēšanas atļauja"** (vai saglabāšana, eksports): atzīmējiet to sadaļā {{ui:Asistenti}} un tad jautājiet vēlreiz.
- **"Lietotājs novieto elementu":** pabeidziet, ko darāt (vai nospiediet {{key:Esc}}), tad ļaujiet asistentam mēģināt vēlreiz.
- **Kļūdas "401" vai "token":** token mainījās (Studio tika restartēts vai {{ui:Jauns token}}). Ievietojiet jauno asistenta iestatījumos.

## Skatiet arī

- [Receptes AI asistentiem](common:assistants-recipes): darba piemēri, katrs ar rīkiem, ko tas izsauc.

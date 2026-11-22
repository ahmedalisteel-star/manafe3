---
title: Usare Manafe3 con un assistente IA
summary: Lasciare che il proprio assistente IA o script legga il modello, le sue parti, i problemi e le interferenze, aggiunga aste e collegamenti, salvi ed esporti (anche USD): permessi, collegamento tramite Manafe3 Desktop e registro attività.
keywords: ia, assistente, agente, mcp, model context protocol, script, automazione, parti, interferenze, collegamenti, permessi, disconnetti, attività, annulla
from: d624c9a0
---

## Cosa si impara

Come lasciare che un assistente IA (o uno script scritto da sé) lavori con Manafe3, e come decidere che cosa può toccare.

Manafe3 **non ha un'IA propria** e non invia nulla da nessuna parte. Si porta l'assistente: qualsiasi programma che parla il Model Context Protocol (MCP). Manafe3 gli fornisce soltanto strumenti, e si scelgono quali.

## Attivarlo

1. Aprire {{ui:Impostazioni}} (l'ingranaggio nella barra dell'app, oppure {{key:Mod+,}}) e andare alla scheda {{ui:Manafe3}}.
2. Sotto {{ui:Assistenti}}, spuntare **Consenti agli assistenti IA e agli script di usare Manafe3**. È disattivato finché non lo si attiva.
3. Scegliere che cosa può fare: **Lettura** è spuntata all'inizio; spuntare **Modifica**, **Salva** o **Esporta** solo quando servono.

Gli strumenti al di fuori dei permessi spuntati non vengono offerti all'assistente; se lo chiede comunque, Manafe3 lo rifiuta e lo scrive nel registro attività. Disattivare l'interruttore chiude subito ogni collegamento.

## Collegare l'assistente

Gli assistenti si collegano tramite **Manafe3 Desktop** sul proprio computer: Studio avvia un piccolo server raggiungibile solo da questo computer, protetto da un token che genera ogni volta che si avvia. In Studio, scegliere {{ui:Collega un assistente}} e copiare indirizzo e token nel proprio assistente (Studio mostra le impostazioni esatte da incollare). Non condividere mai il token.

:::note
Una scheda del browser non può aprire un collegamento per un assistente: nelle app browser l'interruttore non ha effetto finché non si usa Manafe3 Desktop sul proprio computer.
:::

## Il controllo resta a sé

- **Ogni modifica è un unico passo di annullamento**, etichettato come dell'assistente (per esempio "Assistente: aggiungi trave", "Assistente: aggiungi fazzoletti"). {{key:Mod+Z}} annulla nel complesso l'ultima modifica dell'assistente. Il comando `undo` dell'assistente annulla solo i suoi passi, mai quelli propri, a meno che non lo chieda esplicitamente.
- **Attende il proprio turno.** Mentre si posiziona un'asta, si spostano parti o si incolla, Manafe3 rifiuta le modifiche dell'assistente e gli dice di riprovare.
- **Si sa quando ne è collegato uno.** Un pulsante nella barra dell'app indica l'assistente mentre è collegato; fare clic per vedere che cosa può fare, oppure per **Disconnetti**.
- **Attività.** {{ui:Impostazioni}} › {{ui:Manafe3}} › {{ui:Assistenti}} › {{ui:Attività}} elenca ogni chiamata: quando, quale strumento, eseguita o rifiutata. {{ui:Salva il registro}} ne conserva una copia.

## Che cosa può chiedere un assistente

Tutte le lunghezze sono in millimetri, i punti `[x, y, z]` con z verso l'alto, come nel modello.

| Strumento | Permesso | Cosa fa |
|---|---|---|
| `app_info`, `model_describe` | Lettura | Il modello aperto: griglie, livelli, fasi, aste per tipo e profilo, collegamenti, fondazioni, scale, parti, peso dell'acciaio, problemi |
| `parts_list` | Lettura | Marchi dei pezzi con profilo, materiale, lunghezza di taglio, quantità, peso, fase e marchi di assieme; per tipo, profilo, marchio o fase |
| `problems_list` | Lettura | Ciò che elenca la scheda {{ui:Problemi}}, ciascuno con l'oggetto a cui si riferisce |
| `clash_check` | Lettura | La [verifica delle interferenze](topic:clash-check), con la sua tolleranza e le fasi |
| `selection_get` | Lettura | Ciò che è selezionato |
| `selection_set` | Modifica | Seleziona aste, collegamenti, fondazioni o scale (per id o marchio del pezzo) per mostrarli; non cambia nulla |
| `member_add` | Modifica | Una trave, un pilastro, un controvento o una piastra tra due punti |
| `connection_add` | Modifica | Piastre di testata, piatti di taglio, piastre di base, giunzioni o fazzoletti dove si incontrano le aste indicate, come fanno i pulsanti {{ui:Collega}} |
| `undo` | Modifica | Annulla gli ultimi passi dell'assistente |
| `model_save` | Salva | Il salvataggio di Manafe3 |
| `model_export` | Esporta | IFC, file NC, distinta base, schema di piegatura, file KISS o distinta di taglio, come fanno i pulsanti {{ui:Uscita}} |
| `usd_export` | Esporta | Il modello in acciaio come USD (.usda, .usdc o .usdz), come lo scrive {{ui:Uscita}} › {{ui:USD}} (vedi [Esporta il modello in acciaio come USD](topic:usd)); in Studio può scrivere il file in una cartella che si è autorizzata |

## Se qualcosa non funziona

- **L'assistente non vede strumenti Manafe3:** controllare che l'interruttore sia attivo in questa finestra e che la finestra sia aperta in Studio.
- **"richiede il permesso di modifica"** (oppure salvataggio, esportazione): spuntarlo sotto {{ui:Assistenti}}, poi richiedere di nuovo.
- **"La persona sta posizionando un'asta":** terminare ciò che si sta facendo (oppure premere {{key:Esc}}), poi lasciare che l'assistente riprovi.
- **Errori "401" o "token":** il token è cambiato (Studio è stato riavviato, oppure {{ui:Nuovo token}}). Copiare il nuovo token nelle impostazioni dell'assistente.

## Vedi anche

- [Ricette per gli assistenti IA](common:assistants-recipes): esempi svolti, ciascuno con gli strumenti che chiama.

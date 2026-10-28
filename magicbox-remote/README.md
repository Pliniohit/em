# Controle Projetor (iPhone → Magic Box pelo navegador)

Página web aberta no Safari do iPhone. Ela tem touchpad com cursor, setas e OK, Voltar/Início/Menu/Apps, volume, play/pause e teclado ao vivo. Um servidor Python repassa tudo ao projetor por ADB, pelo Wi-Fi.

```
iPhone (Safari) --Wi-Fi--> controle.py --adb--> Magic Box (Android)
```

## 1. Preparar a Magic Box (uma vez só)
1. Configurações > Sobre > toque 7x em **Número da versão** para liberar as Opções do desenvolvedor.
2. Opções do desenvolvedor > ligue **Depuração USB / ADB** (e **ADB pela rede**, se aparecer).
3. Anote o IP do projetor (Configurações > Rede).

## 2A. Servidor no notebook (mais simples)
Requisitos: Python 3 e `adb` (Android platform-tools).
```
python controle.py --adb 192.168.0.50:5555
```
Na primeira conexão, aceite o aviso "Permitir depuração" na tela projetada.

## 2B. Servidor no próprio projetor (sem notebook)
Instale o Termux (APK do F-Droid) na Magic Box e rode no Termux:
```
pkg install python android-tools
adb connect localhost:5555
python controle.py --adb localhost:5555
```
Se a porta 5555 recusar, ligue o projetor uma vez por USB num computador e rode `adb tcpip 5555`. Isso vale até o próximo reboot.

## 3. No iPhone
Abra o link que o terminal imprime, no formato `http://IP:8080/?k=CODIGO`, com o iPhone no mesmo Wi-Fi. Depois use Compartilhar > **Adicionar à Tela de Início** para virar um app.

## Travas e limites
- **Código de acesso `?k=`**: sem ele a página responde 403. Isso impede que qualquer pessoa na rede do evento controle o projetor. O código muda a cada execução; para fixar, use `--token MEUCODIGO`.
- O Android não mostra ponteiro de mouse via ADB. O cursor aparece **no touchpad do iPhone**, no retângulo 16:9 que representa a tela. Em menus, as setas e o OK são mais precisos.
- Os acentos são removidos ao digitar (limite do `input text` do Android).
- Cada toque tem cerca de 0,2 a 0,5 s de atraso, que é o tempo do `input` do Android.
- Teste sem projetor: `python controle.py --dry-run`.

# 🚗 Luxury-Wheels

O **Luxury-Wheels** é uma plataforma web completa para a consulta e reserva de automóveis de luxo, desenvolvida em **Python** com o ecossistema **Flask**. A aplicação conta com um sistema robusto de autenticação de utilizadores, gestão de datas para aluguer e consultas avançadas a uma base de dados relacional.

## 🚀 Funcionalidades Principais
* 🔐 **Autenticação Segura:** Sistema de registo e login com encriptação de palavras-passe (Werkzeug Security) e controlo de sessões (Flask-Login).
* 📅 **Gestão de Reservas Temporais:** Controlo de períodos de aluguer, validação de disponibilidade e cálculo de durações de reserva.
* 🔍 **Filtros Avançados:** Motor de busca inteligente na base de dados utilizando operadores lógicos (`AND` / `OR`).
* ✉️ **Mensagens Flash:** Feedback visual em tempo real para o utilizador após ações do sistema (sucesso, alertas ou erros).

## 🛠️ Tecnologias Utilizadas
* **Backend:** Python 3, Flask, Flask-Login, Werkzeug
* **Base de Dados:** Flask-SQLAlchemy / SQLAlchemy ORM
* **Frontend:** HTML5, CSS3

## 📦 Dependências Necessárias (`requirements.txt`)
Para que o projeto funcione, garanta que o seu ficheiro `requirements.txt` contém:
```text
Flask
Flask-SQLAlchemy
Flask-Login
```

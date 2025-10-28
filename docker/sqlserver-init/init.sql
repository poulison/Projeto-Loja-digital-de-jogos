IF DB_ID('marketdb') IS NULL
BEGIN
    CREATE DATABASE marketdb;
END;
GO

USE marketdb;
GO

-- Criação da tabela de clientes (com nomes em português)
IF OBJECT_ID('dbo.Clientes','U') IS NULL
BEGIN
    CREATE TABLE dbo.Clientes(
        IdCliente INT IDENTITY(1,1) PRIMARY KEY,              -- Identificador único
        Nome NVARCHAR(120) NOT NULL,                          -- Nome completo
        Email NVARCHAR(200) NOT NULL UNIQUE,                  -- E-mail do cliente
        Telefone NVARCHAR(20) NULL,                           -- Telefone
        CPF NVARCHAR(14) NULL UNIQUE,                         -- CPF formatado
        DataNascimento DATE NULL,                             -- Data de nascimento
        Rua NVARCHAR(200) NULL,                               -- Endereço - Rua
        Cidade NVARCHAR(100) NULL,                            -- Endereço - Cidade
        Estado NVARCHAR(50) NULL,                             -- Endereço - Estado
        CEP NVARCHAR(15) NULL,                                -- Código postal
        PlataformaFavorita NVARCHAR(50) NULL,                 -- Ex: PS5, PC, Xbox
        DataCadastro DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()  -- Data de registro
    );
END;
GO

-- Inserção de alguns clientes de exemplo
IF NOT EXISTS (SELECT 1 FROM dbo.Clientes)
BEGIN
    INSERT INTO dbo.Clientes
    (Nome, Email, Telefone, CPF, DataNascimento, Rua, Cidade, Estado, CEP, PlataformaFavorita)
    VALUES
    ('Mariane Izidoro', 'mari@example.com', '(11) 98888-7777', '123.456.789-00', '2002-08-15',
     'Rua das Flores, 123', 'São Paulo', 'SP', '01234-000', 'PS5'),

    ('Guilherme Santos', 'gui@example.com', '(11) 97777-6666', '987.654.321-00', '2001-02-10',
     'Av. Paulista, 500', 'São Paulo', 'SP', '01310-000', 'PC'),

    ('Lucas Pereira', 'lucas@example.com', '(21) 99999-5555', '222.333.444-55', '1999-05-25',
     'Rua dos Games, 45', 'Rio de Janeiro', 'RJ', '22000-000', 'Xbox');
END;
GO

-- Consulta para verificar os dados
SELECT * FROM dbo.Clientes;

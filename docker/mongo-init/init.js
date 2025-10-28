// Conecta ao DB
const db = connect("mongodb://localhost:27017/marketdb");

// Coleção de jogos
db.createCollection("games");

// Índices:
// - SKU único para identificar o jogo
// - Índice composto por plataforma + gênero para filtros comuns
// - Índice de texto em título para busca
db.games.createIndex({ sku: 1 }, { unique: true });
db.games.createIndex({ platform: 1, genre: 1 });
db.games.createIndex({ title: "text" });

// Seed inicial (apenas se estiver vazio)
if (db.games.countDocuments() === 0) {
  db.games.insertMany([
    {
      sku: "PS5-001",
      title: "Spider-Man 2",
      platform: "PS5",
      genre: "Action",
      price: 299.90,
      stock: 15,
      pegi: 16
    },
    {
      sku: "PS5-002",
      title: "Horizon Forbidden West",
      platform: "PS5",
      genre: "RPG",
      price: 279.90,
      stock: 20,
      pegi: 16
    },
    {
      sku: "PC-001",
      title: "Baldur's Gate 3",
      platform: "PC",
      genre: "RPG",
      price: 199.99,
      stock: 30,
      pegi: 18
    }
  ]);
}

// Mostra o que ficou
printjson(db.games.find().toArray());

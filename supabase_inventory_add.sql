-- SQL ADDITIF - Système d'Inventaire et Objets --

-- 1. Table de définition globale des objets (Catalog)
CREATE TABLE IF NOT EXISTS public.items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), -- ID généré automatiquement par Supabase
    name text NOT NULL,
    description text
);

-- 2. Table de liaison Personnage <-> Objets (Inventaire)
CREATE TABLE IF NOT EXISTS public.inventory (
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    item_id uuid REFERENCES public.items(id) ON DELETE CASCADE,
    quantity integer NOT NULL DEFAULT 1,
    -- Clé primaire multiple pour s'assurer qu'un perso n'a qu'une seule de "Pelle" qui s'incrémente (quantité) et pas 50 lignes distinctes.
    PRIMARY KEY (user_id, guild_id, item_id),
    -- S'assure que le personnage existe (lier à la bonne session par server)
    FOREIGN KEY (user_id, guild_id) REFERENCES public.characters(user_id, guild_id) ON DELETE CASCADE
);

-- Note : L'administrateur peut utiliser '/item-add' pour peupler le catalogue de 'items', puis '/give-item' avec l'ID (ou l'ID court) généré !

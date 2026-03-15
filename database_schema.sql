-- ==== SCHÉMA COMPLET BASE DE DONNÉES - BOT CHARNOXIA ==== --
-- Ce fichier contient toute la structure pour recréer la DB de zéro --

-- 1. TABLES DE RÉFÉRENCES 
CREATE TABLE IF NOT EXISTS public.domes (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS public.banks (
    id text PRIMARY KEY, 
    name text NOT NULL, 
    description text
);

CREATE TABLE IF NOT EXISTS public.central_bank (
    id integer PRIMARY KEY DEFAULT 1,
    name text NOT NULL DEFAULT 'Banque Fédérale Charnoxia',
    total_reserves bigint NOT NULL DEFAULT 1000000000, 
    updated_at timestamp with time zone DEFAULT now()
);

-- 2. TABLE PRINCIPALE: PERSONNAGES
CREATE TABLE IF NOT EXISTS public.characters (
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL DEFAULT 0,
    first_name text NOT NULL DEFAULT 'Inconnu',
    last_name text NOT NULL DEFAULT 'Inconnu',
    birth_date date,
    role text NOT NULL, 
    dome text REFERENCES public.domes(name) ON DELETE SET NULL,
    is_contaminated boolean NOT NULL DEFAULT false,
    balance integer NOT NULL DEFAULT 0,
    bank integer NOT NULL DEFAULT 0, -- Rendra obsolète avec bank_accounts mais conservé pour compatibilité temporaire
    avatar_url text,
    id_card_url text,
    created_at timestamp with time zone DEFAULT now(),
    PRIMARY KEY (user_id, guild_id)
);

-- 3. TABLES D'ÉCONOMIE: COMPTES ET TRANSACTIONS
CREATE TABLE IF NOT EXISTS public.bank_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    bank_id text REFERENCES public.banks(id) ON DELETE CASCADE,
    balance integer NOT NULL DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(user_id, guild_id, bank_id) 
);

CREATE TABLE IF NOT EXISTS public.bank_transactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    bank_id text, -- Optionnel pour les vieilles transactions
    transaction_type text NOT NULL,
    amount integer NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- 4. DONNÉES DE BASE (INSERTS)
INSERT INTO public.central_bank (id, name, total_reserves) VALUES (1, 'Banque Fédérale Charnoxia', 1000000000) ON CONFLICT (id) DO NOTHING;

INSERT INTO public.domes (name) VALUES 
('aurelis'), ('verdancia'), ('lumivor'), ('crysalis'), ('solarion'), 
('nivara'), ('célestium'), ('virelia'), ('obsidara'), ('eryndor'), 
('thaliora'), ('argovian'), ('zephyrian'), ('orivane')
ON CONFLICT DO NOTHING;

INSERT INTO public.banks (id, name, description) VALUES 
('CHX', 'Banque Fédérale Charnoxia', 'La banque centrale et historique. Sûre et fiable.'),
('NVS', 'Nox Vault Systems', 'Des coffres hypersécurisés à l''épreuve de la contamination.'),
('EXP', 'Guilde des Explorateurs', 'Services monétaires pour les voyageurs de l''extrême.')
ON CONFLICT DO NOTHING;

-- 5. POLITIQUES DE SÉCURITÉ POUR LES IMAGES (STORAGE)
-- Accès complet aux INSERTS/UPDATES pour le dossier "avatars" et "ids" 
-- (À exécuter uniquement si RLS actif sur les Storage buckets)
-- CREATE POLICY "Allow public inserts" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'avatars');
-- CREATE POLICY "Allow public updates" ON storage.objects FOR UPDATE USING (bucket_id = 'avatars');
-- CREATE POLICY "Allow public inserts ids" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'ids');
-- CREATE POLICY "Allow public updates ids" ON storage.objects FOR UPDATE USING (bucket_id = 'ids');

"""
Migration: Replace existing FULLTEXT index on Info.name with ngram parser.
Existing ft_book_info_name uses the default (whitespace) parser — not suitable for Korean.
This drops it and recreates with ngram parser for n-gram tokenization.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Safe drop using procedure: ignore error if index does not exist
                """
                CREATE PROCEDURE IF NOT EXISTS _drop_idx_if_exists(tbl VARCHAR(64), idx VARCHAR(64))
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.statistics
                        WHERE table_schema = DATABASE()
                          AND table_name = tbl
                          AND index_name = idx
                    ) THEN
                        SET @sql = CONCAT('ALTER TABLE `', tbl, '` DROP INDEX `', idx, '`');
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END
                """,
                "CALL _drop_idx_if_exists('book_info', 'ft_book_info_name')",
                "CALL _drop_idx_if_exists('book_info', 'ft_info_name_ngram')",
                "DROP PROCEDURE IF EXISTS _drop_idx_if_exists",
                "ALTER TABLE book_info ADD FULLTEXT INDEX ft_info_name_ngram (name) WITH PARSER ngram",
            ],
            reverse_sql=[
                """
                CREATE PROCEDURE IF NOT EXISTS _drop_idx_if_exists(tbl VARCHAR(64), idx VARCHAR(64))
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.statistics
                        WHERE table_schema = DATABASE()
                          AND table_name = tbl
                          AND index_name = idx
                    ) THEN
                        SET @sql = CONCAT('ALTER TABLE `', tbl, '` DROP INDEX `', idx, '`');
                        PREPARE stmt FROM @sql;
                        EXECUTE stmt;
                        DEALLOCATE PREPARE stmt;
                    END IF;
                END
                """,
                "CALL _drop_idx_if_exists('book_info', 'ft_info_name_ngram')",
                "DROP PROCEDURE IF EXISTS _drop_idx_if_exists",
                "ALTER TABLE book_info ADD FULLTEXT INDEX ft_book_info_name (name)",
            ],
        ),
    ]

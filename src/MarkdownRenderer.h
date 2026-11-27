/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QString>

/**
 * Renders Markdown (GitHub-flavoured subset) to the HTML subset understood by
 * QTextDocument: headings, bold/italic/strikethrough, inline code, fenced code
 * blocks, nested ordered/unordered lists, blockquotes, pipe tables, links,
 * images and horizontal rules.
 *
 * Fenced code blocks tagged ```chart / ```chart:bar / ```chart:line are rendered
 * as SVG charts (bar or line) drawn with QtSvg, rasterised to a PNG in the
 * cache directory and embedded as a local image, so no third-party markdown
 * library is needed.
 */
class MarkdownRenderer
{
public:
    static QString render(const QString &markdown);

private:
    static QString renderInline(const QString &text);
    static QString renderListBlock(const QStringList &lines);
    static QString renderTable(const QString &headerLine, const QString &separatorLine, const QStringList &bodyLines);
    static QString renderChart(const QString &info, const QString &body);
};

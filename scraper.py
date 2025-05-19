# scraper_improved.py
import httpx
from bs4 import BeautifulSoup, Tag
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from models import ContestModel, ProblemModel, ProblemDetailModel, SampleTestCase
from datetime import datetime
import re
import copy
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

class ScraperException(Exception):
    pass

class AtCoderScraper:
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.kenkoo_api = "https://kenkoooo.com/atcoder/atcoder-api/v3"
        self.atcoder_base = "https://atcoder.jp"
        
    def _make_request(self, url: str) -> dict:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise ScraperException(f"Error making request to {url}: {str(e)}")

    def _make_html_request(self, url: str) -> str:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise ScraperException(f"Error making request to {url}: {str(e)}")    
    def _clean_section(self, section: Tag) -> str:
        """Clean and format a section's content with improved handling"""
        if not section:
            return ""

        # Deep copy to avoid modifying original
        section = copy.deepcopy(section)
        
        # Remove copy buttons and other non-content elements
        for remove_elem in section.select('.div-btn-copy, .btn-copy, script, .btn-copy-all'):
            remove_elem.decompose()

        # First get all paragraphs in order from the section
        text_parts = []
        for elem in section.find_all(['p', 'pre', 'ul', 'ol']):
            # Clean up the element
            elem_text = elem.get_text(strip=True, separator=' ')
            if elem_text:
                # Add appropriate spacing based on element type
                if elem.name == 'pre':
                    text_parts.append(f"\n{elem_text}\n")
                elif elem.name in ['ul', 'ol']:
                    # Handle bullet points
                    items = [f"- {li.get_text(strip=True)}" for li in elem.find_all('li')]
                    text_parts.append('\n' + '\n'.join(items) + '\n')
                else:
                    text_parts.append(elem_text)

        # Handle LaTeX/KaTeX formulas
        for math in section.select('var, span.katex, span.tex-span'):
            formula = math.get('data-tex', '') or math.get_text(strip=True)
            if formula:
                math.string = f"${formula}$"

        # Handle code blocks
        for pre in section.select('pre'):
            pre_text = pre.get_text().strip()
            if pre_text:
                pre.string = f"\n```\n{pre_text}\n```\n"

        # Handle inline code
        for code in section.select('code'):
            code_text = code.get_text().strip()
            if code_text:
                code.string = f"`{code_text}`"

        # Convert tables to markdown format 
        for table in section.select('table'):
            rows = []
            header = []
            for th in table.select('tr th'):
                header.append(th.get_text(strip=True))
            if header:
                rows.append('| ' + ' | '.join(header) + ' |')
                rows.append('|' + '---|' * len(header))

            for tr in table.select('tr'):
                cells = [td.get_text(strip=True) for td in tr.select('td')]
                if cells:
                    rows.append('| ' + ' | '.join(cells) + ' |')

            if rows:
                table.string = '\n' + '\n'.join(rows) + '\n'

        # Handle line breaks
        for br in section.find_all('br'):
            br.replace_with('\n')

        # Clean text but preserve whitespace
        text = ''
        for child in section.children:
            if isinstance(child, Tag):
                child_text = child.get_text(separator='\n')
            else:
                child_text = str(child)
            if child_text.strip():
                text += child_text + '\n'

        # Clean up whitespace while preserving intentional newlines
        lines = []
        current_block = []
        
        for line in text.splitlines():
            line = line.rstrip()
            if line:
                current_block.append(line)
            elif current_block:
                lines.append(' '.join(current_block))
                lines.append('')  # Keep one blank line
                current_block = []
        
        if current_block:
            lines.append(' '.join(current_block))
            
        # Remove extra blank lines
        return '\n'.join(line for i, line in enumerate(lines) 
                        if line or (i > 0 and i < len(lines)-1 and lines[i-1] and lines[i+1]))

    def get_problem_detail(self, contest_id: str, problem_id: str) -> ProblemDetailModel:
        """Obtains the details of a problem using web scraping with improved content handling"""
        url = f"{self.atcoder_base}/contests/{contest_id}/tasks/{problem_id}"
        html = self._make_html_request(url)
        soup = BeautifulSoup(html, 'lxml')

        # Find task statement container
        task_statement = soup.select_one('#task-statement')
        if not task_statement:
            logger.error("Could not find task-statement element")
            raise ScraperException("Could not find problem content")

        # Get language-specific content (English or Japanese)
        lang_content = None
        for lang in ['en', 'ja']:
            lang_content = task_statement.select_one(f'span.lang-{lang}')
            if lang_content:
                logger.info(f"Found content in language: {lang}")
                break
        if not lang_content:
            logger.warning("No language-specific content found, using full content")
            lang_content = task_statement

        # Section mappings for content parsing
        section_mappings = {
            'statement': ['Problem Statement', 'Problem', '問題文', '問題'],
            'constraints': ['Constraints', '制約', '制約条件'],
            'input_format': ['Input', 'Input Format', '入力', '入力形式'],
            'output_format': ['Output', 'Output Format', '出力', '出力形式'],
            'notes': ['Notes', 'Note', 'Hint', '注意', 'ヒント', '補足']
        }

        # Initialize sections and parse them
        sections = {
            'title': '',
            'statement': '',
            'input_format': '',
            'output_format': '',
            'constraints': '',
            'notes': '',
            'samples': []
        }

        # Extract title
        title_elem = soup.select_one('.h2')
        if title_elem:
            raw_title = title_elem.find(text=True, recursive=False)
            clean_title = raw_title.strip() if raw_title else ""
            sections['title'] = clean_title
            logger.debug(f"Found title: {sections['title']}")

        # Extract score
        score = 100  # Default score
        score_text = lang_content.find(text=lambda t: 'Score' in str(t) or '配点' in str(t))
        if score_text:
            score_matches = re.findall(r'(\d+)', score_text)
            if score_matches:
                try:
                    score = int(score_matches[0])
                    logger.debug(f"Found score: {score}")
                except ValueError:
                    logger.warning("Could not parse score value")

        # Extract time and memory limits
        time_limit = 2.0
        memory_limit = 1024
        limits_text = task_statement.find(text=lambda t: 'Time Limit' in str(t) or 'Memory Limit' in str(t))
        if limits_text:
            time_match = re.search(r'Time Limit[^\d]*(\d+(?:\.\d+)?)', str(limits_text))
            mem_match = re.search(r'Memory Limit[^\d]*(\d+)', str(limits_text))
            if time_match:
                try:
                    time_limit = float(time_match.group(1))
                    logger.debug(f"Found time limit: {time_limit}s")
                except ValueError:
                    logger.warning("Could not parse time limit value")
            if mem_match:
                try:
                    memory_limit = int(mem_match.group(1))
                    logger.debug(f"Found memory limit: {memory_limit}MB")
                except ValueError:
                    logger.warning("Could not parse memory limit value")

        # Process each part section
        current_sample = None
        parts = lang_content.select('div.part')
        for part in parts:
            h3 = part.select_one('h3')
            if not h3:
                continue
            title = h3.get_text(strip=True)
            section_tag = part.select_one('section')
            if not section_tag:
                continue

            content = self._clean_section(section_tag)
            if not content.strip():
                continue

            logger.debug(f"Processing section: {title}")

            # Sample input/output/explanation
            if 'Sample Input' in title or '入力例' in title:
                if current_sample:
                    sections['samples'].append(current_sample)
                current_sample = {'input': content, 'output': '', 'explanation': ''}
                logger.debug("Found sample input")
            elif 'Sample Output' in title or '出力例' in title:
                if current_sample:
                    current_sample['output'] = content
                    logger.debug("Found sample output")
            elif 'Sample Explanation' in title or '出力例の説明' in title:
                if current_sample:
                    current_sample['explanation'] = content
                    logger.debug("Found sample explanation")
            else:
                # Match other sections by keyword
                matched = False
                for key, patterns in section_mappings.items():
                    if any(pattern in title for pattern in patterns):
                        sections[key] = content
                        logger.debug(f"Matched section: {key}")
                        matched = True
                        break
                if not matched:
                    logger.debug(f"Unmapped section: {title}")

        # Add last sample if exists
        if current_sample:
            sections['samples'].append(current_sample)

        # Clean up samples
        cleaned_samples = []
        for sample in sections['samples']:
            if sample['input'].strip() or sample['output'].strip():
                cleaned_samples.append(SampleTestCase(
                    input=sample['input'].strip(),
                    output=sample['output'].strip(),
                    explanation=sample.get('explanation', '').strip()
                ))

        logger.info(f"Successfully extracted problem details with {len(cleaned_samples)} sample cases")

        return ProblemDetailModel(
            contest_id=contest_id,
            problem_id=problem_id,
            title=sections['title'].strip(),
            statement=sections.get('statement', '').strip(),
            input_format=sections.get('input_format', '').strip(),
            output_format=sections.get('output_format', '').strip(),
            constraints=sections.get('constraints', '').strip(),
            notes=sections.get('notes', '').strip(),
            samples=cleaned_samples,
            time_limit=time_limit,
            memory_limit=memory_limit,
            source='atcoder',
            score=score,
            tags=[],
            is_liked=False
        )
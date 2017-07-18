# =============================================================================
# Traph Class
# =============================================================================
#
# Main class representing the Traph data structure.
#
import errno
import os
import re
from collections import defaultdict
from file_storage import FileStorage
from memory_storage import MemoryStorage
from lru_trie import LRUTrie
from traph_write_report import TraphWriteReport
from lru_trie_node import LRU_TRIE_NODE_BLOCK_SIZE
from link_store import LinkStore
from link_store_node import LINK_STORE_NODE_BLOCK_SIZE
from helpers import lru_variations


# Exceptions
class TraphException(Exception):
    pass


# Main class
class Traph(object):

    # =========================================================================
    # Constructor
    # =========================================================================
    def __init__(self, overwrite=False, folder=None,
                 default_webentity_creation_rule=None,
                 webentity_creation_rules=None):

        create = overwrite

        # Solving paths
        if folder:
            lru_trie_path = os.path.join(folder, 'lru_trie.dat')
            link_store_path = os.path.join(folder, 'link_store.dat')

            # Ensuring the given folder exists
            try:
                os.makedirs(folder)
            except OSError as exception:
                if exception.errno == errno.EEXIST and os.path.isdir(folder):
                    pass
                else:
                    raise

            # Testing existence of files
            lru_trie_file_exists = os.path.isfile(lru_trie_path)
            link_store_file_exists = os.path.isfile(link_store_path)

            # Checking consistency
            if lru_trie_file_exists and not link_store_file_exists:
                raise TraphException(
                    'File inconsistency: `lru_trie.dat` file exists but not `link_store.dat`.'
                )

            if not lru_trie_file_exists and link_store_file_exists:
                raise TraphException(
                    'File inconsistency: `link_store.dat` file exists but not `lru_trie.dat`.'
                )

            # TODO: check corruption by mod file size / block

            # Do we need to create the files for the first time?
            create = overwrite or (not lru_trie_file_exists and not link_store_file_exists)

            if create:
                # TODO: erase dir and all its content
                self.lru_trie_file = open(lru_trie_path, 'wb+')
                self.link_store_file = open(link_store_path, 'wb+')
            else:
                self.lru_trie_file = open(lru_trie_path, 'rb+')
                self.link_store_file = open(link_store_path, 'rb+')

            self.lru_trie_storage = FileStorage(
                LRU_TRIE_NODE_BLOCK_SIZE,
                self.lru_trie_file
            )

            self.links_store_storage = FileStorage(
                LINK_STORE_NODE_BLOCK_SIZE,
                self.link_store_file
            )
        else:
            self.lru_trie_storage = MemoryStorage(LRU_TRIE_NODE_BLOCK_SIZE)
            self.links_store_storage = MemoryStorage(LINK_STORE_NODE_BLOCK_SIZE)

        # LRU Trie initialization
        self.lru_trie = LRUTrie(self.lru_trie_storage)

        # Link Store initialization
        self.link_store = LinkStore(self.links_store_storage)

        # Webentity creation rules are stored in RAM
        self.default_webentity_creation_rule = re.compile(
            default_webentity_creation_rule,
            re.I
        )

        self.webentity_creation_rules = {}

        for prefix, pattern in webentity_creation_rules.items():
            self.add_webentity_creation_rule(prefix, pattern, create)


    # =========================================================================
    # Internal methods
    # =========================================================================
    def __generated_web_entity_id(self):
        header = self.lru_trie.header
        header.increment_last_webentity_id()
        header.write()

        return header.last_webentity_id()

    def __add_prefixes(self, prefixes):
        # TODO: deal with edge case where some prefixes are already set
        #       to other and/or different web entities
        # (if not in this function, then at the calls)

        webentity_id = self.__generated_web_entity_id()

        for prefix in prefixes:
            node, history = self.lru_trie.add_lru(prefix)
            node.set_webentity(webentity_id)
            node.write()

        return webentity_id

    def __apply_webentity_creation_rule(self, rule_prefix, lru):
        regexp = self.webentity_creation_rules[rule_prefix]
        match = regexp.search(lru)

        if not match:
            return None

        return match.group()

    def __apply_webentity_default_creation_rule(self, lru):

        regexp = self.default_webentity_creation_rule
        match = regexp.search(lru)

        if not match:
            return None

        return match.group()

    def __add_page(self, lru):
        node, history = self.lru_trie.add_page(lru)

        report = TraphWriteReport()

        # Expected behavior is:
        #   1) Retrieve all creation rules triggered 'above' in the trie
        #   2) Apply them in order to get CANDIDATE prefixes GENERATED by the rule
        #   3) Two cases:
        #      3a) All prefixes are smaller OR EQUAL (upper) than an existing prefix
        #          -> Nothing happens (webentity already exists)
        #      3b) A prefix is STRICTLY longer (lower) than existing prefixes
        #          -> apply the longest prefix as a new webentity

        # Retrieving the longest candidate prefix
        longest_candidate_prefix = ''
        for rule_prefix in history.rules_to_apply():
            candidate_prefix = self.__apply_webentity_creation_rule(rule_prefix, lru)

            if candidate_prefix and len(candidate_prefix) > len(longest_candidate_prefix) :
                longest_candidate_prefix = candidate_prefix

        # In this case, the webentity already exists
        if longest_candidate_prefix and len(longest_candidate_prefix) <= history.webentity_position + 1:
            return node, report

        # Else we need to expand the prefix and create relevant web entities
        if longest_candidate_prefix:
            expanded_prefixes = self.expand_prefix(longest_candidate_prefix)
            webentity_id = self.__add_prefixes(expanded_prefixes)
            report.created_webentities[webentity_id] = expanded_prefixes
            return node, report

        # Nothing worked, we need to apply the default creation rule
        longest_candidate_prefix = self.__apply_webentity_default_creation_rule(lru)
        expanded_prefixes = self.expand_prefix(longest_candidate_prefix)
        webentity_id = self.__add_prefixes(expanded_prefixes)
        report.created_webentities[webentity_id] = expanded_prefixes

        return node, report


    # =========================================================================
    # Public interface
    # =========================================================================
    def index_batch_crawl(self, data):
        # data is supposed to be a JSON of this form:
        # {pages:{'lru':'<lru>', 'lrulinks':[<lrulink1>, ...]}}
        #
        # TODO: return a JSON containing created entities:
        # {stats:{}, webentities:{'<weid>':[<prefix1>, ...]}}
        pass

    def add_webentity_creation_rule(self, rule_prefix, pattern, write_in_trie=True):
        self.webentity_creation_rules[rule_prefix] = re.compile(
            pattern,
            re.I
        )

        report = TraphWriteReport()

        if write_in_trie:
            node, history = self.lru_trie.add_lru(rule_prefix)
            if not node:
                raise Exception('Prefix not in tree: ' + rule_prefix) # TODO: raise custom exception
            node.flag_as_webentity_creation_rule()
            node.write()
            # Spawn necessary web entities
            candidate_prefixes = set()
            for node2, lru in self.lru_trie.dfs_iter(node, rule_prefix[:-1]):
                # Note: unsure why we need to trim rule_prefix above, but it seems to work
                if node2.is_page():
                    _, add_report = self.__add_page(lru)
                    report += add_report

        return report

    def remove_webentity_creation_rule(self, rule_prefix):
        if not self.webentity_creation_rules[rule_prefix]:
            raise Exception('Prefix not in creation rules: ' + rule_prefix) # TODO: raise custom exception
        del self.webentity_creation_rules[rule_prefix]

        node = self.lru_trie.lru_node(rule_prefix)
        if not node:
            raise Exception('Prefix not in tree: ' + rule_prefix) # TODO: raise custom exception
        node.unflag_as_webentity_creation_rule()
        node.write()

        return True

    def create_webentity(self, prefixes, expand=False):
        # TODO
        # Return an error if one of the prefixes is already attributed to a we
        pass

    def delete_webentity(self, weid, weid_prefixes):
        # TODO
        # Note: weid is not strictly necessary, but it helps to check
        #       data consistency
        pass

    def add_webentity_prefix(self, weid, prefix):
        # TODO
        pass

    def remove_webentity_prefix(self, weid, prefix):
        # TODO
        pass

    def retrieve_prefix(self, lru):
        # TODO: return the first webentity prefix above lru
        # Raise an error in lru not in trie
        # Worst case scenario should be default we creation rule:
        # raise an error if no prefix found
        pass

    def retrieve_webentity(self, lru):
        # TODO: return the first webentity id above lru
        # Raise an error in lru not in trie
        # Worst case scenario should be default we creation rule:
        # raise an error if no webentity id found
        pass

    def get_webentity_by_prefix(self, prefix):
        # TODO: return weid
        # If the prefix is not in the trie or not the prefix of
        # an existing webentity, return an error
        pass

    def get_webentity_pages(self, weid, prefixes):
        # TODO: return list of lrus
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentity_crawled_pages(self, weid, prefixes):
        # TODO: return list of lrus
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentity_most_linked_pages(self, weid, prefixes):
        # TODO: return list of lrus
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentity_parent_webentities(self, weid, prefixes):
        # : return list of weid
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentity_child_webentities(self, weid, prefixes):
        # TODO: return list of weid
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentity_pagelinks(self, weid, prefixes, include_internal=False):
        # TODO: return list of [source_lru, target_lru, weight]
        # Note: the prefixes are thoses of the webentity whose id is weid
        # No need to check
        pass

    def get_webentities_links(self):
        # TODO: return all webentity links
        pass

    def expand_prefix(self, prefix):
        return lru_variations(prefix)

    def add_page(self, lru):
        node, report = self.__add_page(lru)

        return report

    def add_links(self, links):
        store = self.link_store
        report = TraphWriteReport()

        # TODO: this will need to return created web entities
        inlinks = defaultdict(list)
        outlinks = defaultdict(list)
        pages = dict()

        for source_page, target_page in links:

            # Adding pages
            if not source_page in pages:
                node, page_report = self.__add_page(source_page)
                report += page_report
                pages[source_page] = node
            if not target_page in pages:
                node, page_report = self.__add_page(target_page)
                report += page_report
                pages[target_page] = node

            # Handling multimaps
            outlinks[source_page].append(target_page)
            inlinks[target_page].append(source_page)

        for source_page, target_pages in outlinks.items():
            source_node = pages[source_page]
            target_blocks = (pages[target_page].block for target_page in target_pages)

            store.add_outlinks(source_node, target_blocks)

        for target_page, source_pages in inlinks.items():
            target_node = pages[target_page]
            source_blocks = (pages[source_page].block for source_page in source_pages)

            store.add_inlinks(target_node, source_blocks)

        return report

    def close(self):

        # Cleanup
        self.lru_trie_file.close()
        self.link_store_file.close()

    def clear(self):
        # TODO
        pass

    # =========================================================================
    # Iteration methods
    # =========================================================================
    def links_iter(self, out=True):
        for page_node, lru in self.lru_trie.pages_iter():
            if not page_node.has_outlinks():
                continue

            for link_node in self.link_store.link_nodes_iter(page_node.outlinks()):
                yield lru, self.lru_trie.windup_lru(link_node.target())

    def pages_iter(self):
        return self.lru_trie.pages_iter()

    def webentity_prefix_iter(self):
        return self.lru_trie.webentity_prefix_iter()

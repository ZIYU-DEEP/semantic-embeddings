import sys
import argparse
import pickle



def read_hierarchy(filename):
    
    hierarchy = {}
    stack = []
    last_node = None
    
    with open(filename) as f:
        for li, l in enumerate(f, start = 1):
            l = l.strip()
            if l != '':
                
                orig_node_name = l.lstrip('- ')
                node_name = orig_node_name.rstrip(' ?')
                parens_pos = node_name.find('(')
                if parens_pos > 0:
                    node_name = node_name[:parens_pos-1]
                if node_name in hierarchy:
                    raise RuntimeError('Duplicate node name: {} (at line {})'.format(node_name, li))
                
                node_level = max(0, len(l) - len(orig_node_name) - 1)
                if node_level % 2 != 0:
                    raise RuntimeError('Incorrect indentation at line {}: {}'.format(li, l))
                node_level //= 2
                if node_level > len(stack) + 1:
                    raise RuntimeError('Unexpectedly deep indentation at line {}: {}'.format(li, l))
                
                if node_level > len(stack):
                    if last_node is None:
                        raise RuntimeError('First line must not be indented.')
                    stack.append(last_node)
                elif node_level < len(stack):
                    stack = stack[:node_level]
                
                hierarchy[node_name] = set()
                if len(stack) > 0:
                    hierarchy[stack[-1]].add(node_name)
                last_node = node_name
    
    return hierarchy


def encode_class_names(hierarchy, initial_labels):
    
    class_names = [lbl for lbl in initial_labels]
    class_ind = { lbl : i for i, lbl in enumerate(class_names) }
    
    hierarchy_names = list(hierarchy.keys())
    for name in hierarchy_names:
        
        if name in class_ind:
            ind = class_ind[name]
        else:
            ind = len(class_names)
            class_ind[name] = ind
            class_names.append(name)
        
        encoded_children = set()
        for child in hierarchy[name]:
            if child in class_ind:
                encoded_children.add(class_ind[child])
            else:
                encoded_children.add(len(class_names))
                class_ind[child] = len(class_names)
                class_names.append(child)
        
        hierarchy[ind] = encoded_children
        del hierarchy[name]
    
    return hierarchy, class_names


def save_hierarchy(hierarchy, filename):
    
    with open(filename, 'w') as f:
        for parent, children in hierarchy.items():
            for child in children:
                f.write('{} {}\n'.format(parent+1, child+1))


def plot_hierarchy(hierarchy, filename):
    
    import pydot
    
    graph = pydot.Dot(graph_type = 'digraph', rankdir = 'LR')
    nodes = { name : pydot.Node(name, style = 'filled', fillcolor = '#ffffff' if len(children) == 0 else '#eaeaea') for name, children in hierarchy.items() }
    for node in nodes.values():
        graph.add_node(node)
    
    for parent, children in hierarchy.items():
        for child in children:
            graph.add_edge(pydot.Edge(nodes[parent], nodes[child]))
    
    graph.write_svg(filename, prog = 'dot')



if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        description='Translates a hierarchy given in indented tree-form into a list of parent-child tuples.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('hierarchy_file', type=str, help='The input file specifying the hierarchy in indented tree format.')
    parser.add_argument('class_names', type=str, default=None,
                        help='Path to a text file associating CUB labels (1-200) with the names of their nodes in the hierarchy. These labels will be maintained.')
    parser.add_argument('--out', type=str, default='cub.parent-child.txt', help='Output file containing parent-child tuples.')
    parser.add_argument('--out_names', type=str, default='class_names.txt', help='Output file associating numerical class labels with their original names.')
    parser.add_argument('--plot', type=str, default=None, help='If given, a plot of the hierarchy will be written to the specified file. Requires the pydot package.')
    args = parser.parse_args()
    
    if args.class_names:
        with open(args.class_names) as f:
            initial_labels = { int(lbl) : node_name for line in f if line.strip() != '' for lbl, node_name in [line.strip().split(maxsplit=1)] }
    else:
        initial_labels = {}
    
    hierarchy = read_hierarchy(args.hierarchy_file)
    if args.plot is not None:
        plot_hierarchy(hierarchy, args.plot)
    hierarchy, node_names = encode_class_names(hierarchy, (classname for _, classname in sorted(initial_labels.items())))
    
    save_hierarchy(hierarchy, args.out)
    
    with open(args.out_names, 'w') as f:
        for ind, name in enumerate(node_names, 1):
            f.write('{} {}\n'.format(ind, name))
